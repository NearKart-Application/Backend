"""
NearKart — Analytics Serializers
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.videos.models import Video
from apps.products.models import Product


class VideoStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ['id', 'title', 'status', 'view_count', 'like_count', 'duration_seconds', 'created_at']


class ProductStatSerializer(serializers.ModelSerializer):
    wishlist_count    = serializers.SerializerMethodField()
    reservation_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'status', 'base_price', 'wishlist_count', 'reservation_count', 'created_at']

    @extend_schema_field(serializers.IntegerField())
    def get_wishlist_count(self, obj):
        return obj.wishlisted_by.count()

    @extend_schema_field(serializers.IntegerField())
    def get_reservation_count(self, obj):
        return obj.reservations.filter(status__in=['pending', 'confirmed']).count()
