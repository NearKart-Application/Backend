"""
NearKart — Product Services
ProductService
"""
import logging
from django.contrib.postgres.search import TrigramSimilarity

from core.utils.cache import CacheService
from core.utils.geo import get_nearby_products

logger = logging.getLogger(__name__)


_CATEGORY_CODES = {
    'fashion':     'FASH',
    'jewellery':   'JEWE',
    'footwear':    'FOOT',
    'decor':       'DECO',
    'furniture':   'FURN',
    'gifts':       'GIFT',
    'beauty':      'BEAU',
    'food':        'FOOD',
    'electronics': 'ELEC',
}


def _store_abbreviation(store) -> str:
    """Return a unique initials-based abbreviation for the store (e.g. VE, VE2)."""
    import re
    from apps.stores.models import Store

    words = re.sub(r'[^a-zA-Z\s]', '', store.name.strip()).split()
    raw = ''.join(w[0].upper() for w in words if w) or 'NS'

    # Count stores with the same raw initials created before this one
    rank = 0
    for s in Store.objects.filter(created_at__lt=store.created_at).order_by('created_at').only('name'):
        s_words = re.sub(r'[^a-zA-Z\s]', '', s.name.strip()).split()
        if ''.join(w[0].upper() for w in s_words if w) == raw:
            rank += 1
    return raw if rank == 0 else f'{raw}{rank + 1}'


def _locality_code(store) -> str:
    """Return a 3-char uppercase alpha code from the store's locality."""
    import re
    src = store.locality or store.address or ''
    alpha = re.sub(r'[^a-zA-Z]', '', src)
    return alpha[:3].upper() if alpha else 'GEN'


class ProductService:

    @staticmethod
    def _generate_product_code(store=None, category: str = '') -> str:
        """Generate NS-{ShopAbbr}-{LocalityCode}-{CategoryCode}-{Unique} product code."""
        import random, string
        from .models import Product

        if store is not None:
            shop_abbr  = _store_abbreviation(store)[:3]   # cap at 3 to keep code ≤20 chars
            loc_code   = _locality_code(store)
            cat_code   = _CATEGORY_CODES.get(category.lower().strip(), 'GEN')
            prefix     = f'NS-{shop_abbr}-{loc_code}-{cat_code}'
        else:
            prefix = 'NS'

        for _ in range(10):
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            code = f'{prefix}-{suffix}'
            if not Product.objects.filter(product_code=code).exists():
                return code
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f'{prefix}-{suffix}'

    @staticmethod
    def create(store, validated_data: dict):
        from .models import Product, StockMovementLog, StockMovementReason
        variants_data = validated_data.pop('variants', [])
        validated_data.setdefault(
            'product_code',
            ProductService._generate_product_code(
                store=store,
                category=validated_data.get('category', ''),
            )
        )
        product = Product.objects.create(store=store, **validated_data)
        for v in variants_data:
            initial_qty = v.get('stock_quantity', 0)
            variant = product.variants.create(**v)
            if initial_qty > 0:
                # Log the initial stock so StockMovementLog has a full history
                StockMovementLog.objects.create(
                    variant=variant,
                    changed_by=None,
                    old_qty=0,
                    new_qty=initial_qty,
                    delta=initial_qty,
                    reason=StockMovementReason.RESTOCK,
                    note='initial stock',
                )
        CacheService.invalidate_store_caches(
            store.location.y,
            store.location.x,
        )
        return product

    @staticmethod
    def update(product, validated_data: dict):
        old_price = product.base_price
        for attr, value in validated_data.items():
            setattr(product, attr, value)
        product.save()
        CacheService.invalidate_store_caches(
            product.store.location.y,
            product.store.location.x,
        )
        # PRICE_DROP_ALERT — notify wishlist customers when base_price drops
        new_price = product.base_price
        if new_price < old_price:
            ProductService._notify_price_drop(product, old_price, new_price)
        return product

    @staticmethod
    def _notify_price_drop(product, old_price, new_price) -> None:
        """Notify all active wishlist customers that base_price dropped."""
        import logging
        logger = logging.getLogger(__name__)
        try:
            from apps.products.models import Wishlist
            from apps.notifications.services import NotificationService
            watchers = Wishlist.objects.filter(product=product).select_related('user')
            for watch in watchers:
                try:
                    NotificationService.notify_price_drop(
                        customer=watch.user,
                        product_name=product.name,
                        product_id=str(product.id),
                        old_price=str(old_price),
                        new_price=str(new_price),
                    )
                except Exception as exc:
                    logger.warning('[products] price_drop notify failed user %s: %s', watch.user_id, exc)
        except Exception as exc:
            logger.warning('[products] _notify_price_drop failed product %s: %s', product.id, exc)

    @staticmethod
    def get_nearby(lat: float, lng: float, radius_km: int = 2, category: str = None, store_id: str = None, limit: int = 200):
        return get_nearby_products(lat, lng, radius_km, category, store_id=store_id, limit=limit)

    @staticmethod
    def search(
        query: str,
        lat: float = None,
        lng: float = None,
        radius_km: int = 5,
        min_price: float = None,
        max_price: float = None,
        min_rating: float = None,
        has_offer: bool = None,
        ordering: str = None,
        limit: int = 200,
    ):
        """
        Algorithm 7 — BM25 hybrid search with price/rating/offer/sort filters.

        Combines PostgreSQL full-text ranking (ts_rank_cd, BM25 approximation)
        with trigram similarity for typo tolerance. Uses 'simple' text config
        so Indian brand names are not stemmed.

        Hybrid score = 0.6 × BM25_rank + 0.4 × trigram_similarity
        """
        from .models import Product
        from django.contrib.postgres.search import (
            SearchVector, SearchQuery, SearchRank, TrigramSimilarity,
        )
        from django.db.models import F, ExpressionWrapper, FloatField, Q, Avg, Count

        search_vector = (
            SearchVector('name', weight='A', config='simple') +
            SearchVector('description', weight='B', config='simple')
        )
        search_query = SearchQuery(query, search_type='plain', config='simple')

        qs = Product.objects.filter(
            status='active',
            is_visible=True,
            store__is_active=True,
            store__is_verified=True,
        ).select_related('store').prefetch_related('variants', 'images').annotate(
            bm25_rank=SearchRank(search_vector, search_query, cover_density=True),
            trigram_score=TrigramSimilarity('name', query),
            hybrid_score=ExpressionWrapper(
                F('bm25_rank') * 0.6 + F('trigram_score') * 0.4,
                output_field=FloatField(),
            ),
            store_avg_rating=Avg('store__reviews__rating'),
        ).filter(
            Q(bm25_rank__gt=0.01) | Q(trigram_score__gt=0.2)
        )

        if lat is not None and lng is not None:
            from django.contrib.gis.geos import Point
            from django.contrib.gis.measure import D
            user_point = Point(lng, lat, srid=4326)
            qs = qs.filter(store__location__dwithin=(user_point, D(km=radius_km)))

        if min_price is not None:
            qs = qs.filter(base_price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(base_price__lte=max_price)
        if min_rating is not None:
            qs = qs.filter(store_avg_rating__gte=min_rating)
        if has_offer:
            qs = qs.filter(store__offers__is_active=True).distinct()

        if ordering == 'price_asc':
            qs = qs.order_by('base_price')
        elif ordering == 'price_desc':
            qs = qs.order_by('-base_price')
        elif ordering == 'rating':
            qs = qs.order_by('-store_avg_rating')
        else:
            qs = qs.order_by('-hybrid_score')

        return qs[:limit]

    @staticmethod
    def toggle_wishlist(user, product):
        from .models import Wishlist
        wishlist, created = Wishlist.objects.get_or_create(user=user, product=product)
        if not created:
            wishlist.delete()
            return False  # removed
        return True  # added
