"""
NearKart — Admin Panel Serializers
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.stores.models import Store
from apps.auth_app.models import User


class AdminStoreSerializer(serializers.ModelSerializer):
    owner_phone = serializers.CharField(source='owner.phone_number', read_only=True)
    owner_name  = serializers.CharField(source='owner.full_name', read_only=True)
    product_count = serializers.SerializerMethodField()
    video_count   = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = [
            'id', 'name', 'category', 'address', 'locality',
            'is_active', 'is_verified', 'is_open',
            'wallet_balance', 'performance_score',
            'owner_phone', 'owner_name',
            'product_count', 'video_count',
            'created_at',
        ]
        read_only_fields = [
            'id', 'address', 'locality', 'owner_phone', 'owner_name',
            'product_count', 'video_count',
            'wallet_balance', 'performance_score', 'created_at',
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_product_count(self, obj):
        return obj.products.count()

    @extend_schema_field(serializers.IntegerField())
    def get_video_count(self, obj):
        return obj.videos.count()


class AdminStoreUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Store
        fields = ['is_active', 'is_verified', 'is_open']


class AdminUserSerializer(serializers.ModelSerializer):
    store_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'phone_number', 'full_name', 'email',
            'role', 'is_active', 'is_staff',
            'store_name', 'created_at',
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_store_name(self, obj):
        if obj.role == 'vendor':
            try:
                return obj.store.name
            except Exception:
                return None
        return None
