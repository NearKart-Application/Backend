"""
NearKart — Product Services
ProductService
"""
import logging
from django.contrib.postgres.search import TrigramSimilarity

from core.utils.cache import CacheService
from core.utils.geo import get_nearby_products

logger = logging.getLogger(__name__)


class ProductService:

    @staticmethod
    def create(store, validated_data: dict):
        from .models import Product
        variants_data = validated_data.pop('variants', [])
        product = Product.objects.create(store=store, **validated_data)
        for v in variants_data:
            product.variants.create(**v)
        CacheService.invalidate_store_caches(
            store.location.y,
            store.location.x,
        )
        return product

    @staticmethod
    def update(product, validated_data: dict):
        for attr, value in validated_data.items():
            setattr(product, attr, value)
        product.save()
        CacheService.invalidate_store_caches(
            product.store.location.y,
            product.store.location.x,
        )
        return product

    @staticmethod
    def get_nearby(lat: float, lng: float, radius_km: int = 2, category: str = None, store_id: str = None):
        return get_nearby_products(lat, lng, radius_km, category, store_id=store_id)

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
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        if min_rating is not None:
            qs = qs.filter(store_avg_rating__gte=min_rating)
        if has_offer:
            qs = qs.filter(store__offers__is_active=True).distinct()

        if ordering == 'price_asc':
            qs = qs.order_by('price')
        elif ordering == 'price_desc':
            qs = qs.order_by('-price')
        elif ordering == 'rating':
            qs = qs.order_by('-store_avg_rating')
        else:
            qs = qs.order_by('-hybrid_score')

        return qs[:30]

    @staticmethod
    def toggle_wishlist(user, product):
        from .models import Wishlist
        wishlist, created = Wishlist.objects.get_or_create(user=user, product=product)
        if not created:
            wishlist.delete()
            return False  # removed
        return True  # added
