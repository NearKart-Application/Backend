"""
NearKart — Product Serializers
"""
from django.db import models
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Product, ProductVariant, ProductImage, Wishlist, ProductReview


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProductVariant
        fields = ['id', 'name', 'sku', 'price', 'stock_quantity']
        read_only_fields = ['id']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProductImage
        fields = ['id', 'image_url', 'is_primary', 'order']
        read_only_fields = ['id']


class ProductSerializer(serializers.ModelSerializer):
    variants      = ProductVariantSerializer(many=True, required=False)
    images        = ProductImageSerializer(many=True, read_only=True)
    store_name    = serializers.CharField(source='store.name', read_only=True)
    store_id      = serializers.UUIDField(source='store.id', read_only=True)
    distance_km   = serializers.SerializerMethodField(read_only=True)
    is_wishlisted = serializers.SerializerMethodField(read_only=True)
    primary_image = serializers.SerializerMethodField(read_only=True)
    stock_total   = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = Product
        fields = [
            'id', 'store_id', 'store_name', 'product_code',
            'name', 'description', 'category',
            'status', 'is_visible', 'base_price',
            'variants', 'images',
            'primary_image', 'stock_total',
            'distance_km', 'is_wishlisted',
            'created_at', 'last_updated_at',
        ]
        read_only_fields = ['id', 'store_id', 'store_name', 'created_at', 'last_updated_at']
        extra_kwargs = {'product_code': {'required': False, 'allow_blank': True}}

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image(self, obj):
        images = list(obj.images.all())
        img = next((i for i in images if i.is_primary), None) or (images[0] if images else None)
        return img.image_url if img else None

    @extend_schema_field(serializers.IntegerField())
    def get_stock_total(self, obj):
        return sum(v.stock_quantity for v in obj.variants.all())

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_is_wishlisted(self, obj):
        if hasattr(obj, '_is_wishlisted'):
            return obj._is_wishlisted
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.wishlisted_by.filter(user=request.user).exists()
        return False

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        product = Product.objects.create(**validated_data)
        for v in variants_data:
            ProductVariant.objects.create(product=product, **v)
        return product

    def update(self, instance, validated_data):
        validated_data.pop('variants', None)
        return super().update(instance, validated_data)


class ProductListSerializer(serializers.ModelSerializer):
    """Compact serializer for list/nearby/search endpoints."""
    store_name    = serializers.CharField(source='store.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    distance_km   = serializers.SerializerMethodField()
    min_price     = serializers.SerializerMethodField()
    # Mobile-compatible aliases
    price         = serializers.DecimalField(source='base_price', max_digits=10, decimal_places=2, read_only=True)
    sale_price    = serializers.SerializerMethodField()
    image         = serializers.SerializerMethodField()
    store         = serializers.SerializerMethodField()
    is_on_sale    = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id', 'product_code', 'store_name', 'name', 'category', 'subcategory',
            'base_price', 'min_price', 'primary_image',
            'distance_km', 'status',
            # mobile-compatible fields
            'price', 'sale_price', 'image', 'store', 'is_on_sale', 'festival_tag',
        ]

    def _primary_image(self, obj):
        """Returns first primary (or any) image using prefetch cache — zero DB hit."""
        images = list(obj.images.all())
        img = next((i for i in images if i.is_primary), None) or (images[0] if images else None)
        return img.image_url if img else None

    def _cheapest_variant(self, obj):
        """Returns lowest-price variant using prefetch cache — zero DB hit."""
        variants = list(obj.variants.all())
        return min(variants, key=lambda v: v.price, default=None)

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image(self, obj):
        return self._primary_image(obj)

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None

    @extend_schema_field(serializers.CharField())
    def get_min_price(self, obj):
        v = self._cheapest_variant(obj)
        return str(v.price) if v else str(obj.base_price)

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image(self, obj):
        return self._primary_image(obj)

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_sale_price(self, obj):
        v = self._cheapest_variant(obj)
        if v and float(v.price) < float(obj.base_price):
            return float(v.price)
        return None

    @extend_schema_field(serializers.DictField())
    def get_store(self, obj):
        store = obj.store
        rating = float(getattr(store, 'avg_rating', None) or 0)
        review_count = int(getattr(store, 'review_count_ann', None) or 0)
        return {
            'id': str(store.id),
            'name': store.name,
            'avatar': store.logo_url or None,
            'rating': rating,
            'review_count': review_count,
        }

    @extend_schema_field(serializers.BooleanField())
    def get_is_on_sale(self, obj):
        v = self._cheapest_variant(obj)
        return bool(v and float(v.price) < float(obj.base_price))


class MobileProductDetailSerializer(serializers.ModelSerializer):
    """Mobile-compatible product detail serializer."""
    price        = serializers.DecimalField(source='base_price', max_digits=10, decimal_places=2, read_only=True)
    sale_price   = serializers.SerializerMethodField()
    images       = serializers.SerializerMethodField()
    store        = serializers.SerializerMethodField()
    distance_km  = serializers.SerializerMethodField()
    sizes        = serializers.SerializerMethodField()
    colors       = serializers.SerializerMethodField()
    stock_count  = serializers.SerializerMethodField()
    is_on_sale   = serializers.SerializerMethodField()
    is_wishlisted = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'description', 'category', 'subcategory',
            'price', 'sale_price', 'images', 'store',
            'distance_km', 'sizes', 'colors',
            'stock_count', 'is_on_sale', 'festival_tag', 'is_wishlisted',
        ]

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_sale_price(self, obj):
        variant = min(obj.variants.all(), key=lambda v: v.price, default=None)
        if variant and float(variant.price) < float(obj.base_price):
            return float(variant.price)
        return None

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_images(self, obj):
        # Sort prefetched images in Python — avoids bypassing the prefetch cache
        return [img.image_url for img in sorted(obj.images.all(), key=lambda i: i.order)]

    @extend_schema_field(serializers.DictField())
    def get_store(self, obj):
        from django.db.models import Avg, Count
        agg = obj.store.reviews.aggregate(avg=Avg('rating'), cnt=Count('id'))
        return {
            'id':           str(obj.store.id),
            'name':         obj.store.name,
            'avatar':       obj.store.logo_url or None,
            'rating':       round(float(agg['avg'] or 0), 1),
            'review_count': agg['cnt'] or 0,
        }

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None

    @extend_schema_field(serializers.ListField())
    def get_sizes(self, obj):
        # Compute from prefetched variants in Python — eliminates N sub-queries per size
        stock_by_size: dict = {}
        for v in sorted(obj.variants.all(), key=lambda v: v.name):
            size = v.name.split('/')[0].strip()
            stock_by_size[size] = stock_by_size.get(size, 0) + (v.stock_quantity or 0)
        return [{'size': s, 'stock': cnt} for s, cnt in stock_by_size.items()]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_colors(self, obj):
        colors = []
        seen = set()
        for v in sorted(obj.variants.all(), key=lambda v: v.name):
            parts = v.name.split('/')
            if len(parts) > 1:
                color = parts[1].strip()
                if color not in seen:
                    seen.add(color)
                    colors.append(color)
        return colors

    @extend_schema_field(serializers.IntegerField())
    def get_stock_count(self, obj):
        return sum(v.stock_quantity or 0 for v in obj.variants.all())

    @extend_schema_field(serializers.BooleanField())
    def get_is_on_sale(self, obj):
        variant = min(obj.variants.all(), key=lambda v: v.price, default=None)
        return bool(variant and float(variant.price) < float(obj.base_price))

    @extend_schema_field(serializers.BooleanField())
    def get_is_wishlisted(self, obj):
        if hasattr(obj, '_is_wishlisted'):
            return obj._is_wishlisted
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.wishlisted_by.filter(user=request.user).exists()
        return False


class ProductReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProductReview
        fields = ['id', 'rating', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value


class ProductReviewListSerializer(serializers.ModelSerializer):
    """Public read — shows reviewer name initials, not phone."""
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model  = ProductReview
        fields = ['id', 'reviewer_name', 'rating', 'content', 'created_at']

    @extend_schema_field(serializers.CharField())
    def get_reviewer_name(self, obj):
        name = getattr(obj.reviewer, 'full_name', '') or ''
        if name:
            parts = name.split()
            return f'{parts[0]} {"*" * (len(parts[1]) if len(parts) > 1 else 0)}'.strip()
        phone = obj.reviewer.phone_number or ''
        return phone[:4] + '****' + phone[-2:] if len(phone) >= 6 else '****'
