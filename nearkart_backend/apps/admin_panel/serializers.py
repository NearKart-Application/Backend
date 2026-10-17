"""
NearKart — Admin Panel Serializers
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.stores.models import Store, WebsiteRequest
from apps.auth_app.models import User
from apps.products.models import Product
from .models import Category, OfferTemplate


class AdminStoreSerializer(serializers.ModelSerializer):
    owner_phone      = serializers.CharField(source='owner.phone_number', read_only=True)
    owner_name       = serializers.CharField(source='owner.full_name', read_only=True)
    owner_profile_id = serializers.CharField(source='owner.profile_id', read_only=True)
    product_count    = serializers.SerializerMethodField()
    video_count      = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = [
            'id', 'name', 'category', 'address', 'locality',
            'is_active', 'is_verified', 'is_open', 'store_type',
            'wallet_balance', 'performance_score',
            'owner_phone', 'owner_name', 'owner_profile_id',
            'product_count', 'video_count',
            'license_url', 'gst_url',
            'created_at',
        ]
        read_only_fields = [
            'id', 'address', 'locality', 'owner_phone', 'owner_name', 'owner_profile_id',
            'product_count', 'video_count',
            'license_url', 'gst_url',
            'wallet_balance', 'performance_score', 'created_at',
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_product_count(self, obj):
        # Use annotation from view when available (avoids N+1 queries)
        return getattr(obj, 'product_count', None) if hasattr(obj, 'product_count') else obj.products.count()

    @extend_schema_field(serializers.IntegerField())
    def get_video_count(self, obj):
        return getattr(obj, 'video_count', None) if hasattr(obj, 'video_count') else obj.videos.count()


class AdminStoreUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Store
        fields = ['is_active', 'is_verified', 'is_open', 'store_type']


class AdminUserSerializer(serializers.ModelSerializer):
    store_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'phone_number', 'full_name', 'email',
            'role', 'is_active', 'is_staff',
            'is_suspended', 'suspension_reason',
            'profile_id', 'admin_assigned_city', 'store_name', 'created_at',
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_store_name(self, obj):
        if obj.role == 'vendor':
            # uses prefetched 'stores' cache — no extra query per user
            store = next(iter(obj.stores.all()), None)
            return store.name if store else None
        return None


class AdminProductSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    image_count   = serializers.SerializerMethodField()
    variant_count = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'category', 'subcategory',
            'status', 'base_price', 'is_visible',
            'store_name', 'image_count', 'variant_count', 'created_at',
        ]
        read_only_fields = [
            'id', 'store_name', 'image_count', 'variant_count', 'created_at',
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_image_count(self, obj):
        return getattr(obj, 'image_count', None) if hasattr(obj, 'image_count') else obj.images.count()

    @extend_schema_field(serializers.IntegerField())
    def get_variant_count(self, obj):
        return getattr(obj, 'variant_count', None) if hasattr(obj, 'variant_count') else obj.variants.count()


class AdminWebsiteRequestSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_id   = serializers.CharField(source='store.id', read_only=True)

    class Meta:
        model  = WebsiteRequest
        fields = [
            'id', 'store_id', 'store_name', 'status',
            'domain_preference', 'notes', 'admin_notes',
            'reviewed_at', 'created_at',
        ]
        read_only_fields = ['id', 'store_id', 'store_name', 'created_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['id', 'name', 'slug', 'icon', 'display_order', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['name', 'slug', 'icon', 'display_order', 'is_active']


class OfferTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OfferTemplate
        fields = [
            'id', 'name', 'description_template', 'default_discount_pct',
            'badge_text', 'emoji', 'image_url', 'is_active', 'is_default',
            'display_order', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
