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
    def search(query: str, lat: float = None, lng: float = None, radius_km: int = 5):
        from .models import Product
        qs = Product.objects.filter(
            status='active',
            is_visible=True,
            store__is_active=True,
            store__is_verified=True,
        ).select_related('store').prefetch_related('variants', 'images').annotate(
            similarity=TrigramSimilarity('name', query)
        ).filter(
            similarity__gt=0.2
        ).order_by('-similarity')

        if lat is not None and lng is not None:
            from django.contrib.gis.geos import Point
            from django.contrib.gis.measure import D
            user_point = Point(lng, lat, srid=4326)
            qs = qs.filter(store__location__dwithin=(user_point, D(km=radius_km)))

        return qs[:30]

    @staticmethod
    def toggle_wishlist(user, product):
        from .models import Wishlist
        wishlist, created = Wishlist.objects.get_or_create(user=user, product=product)
        if not created:
            wishlist.delete()
            return False  # removed
        return True  # added
