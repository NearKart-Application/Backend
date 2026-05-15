"""
NearKart — Product Serializers
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Product, ProductVariant, ProductImage, Wishlist


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
    variants     = ProductVariantSerializer(many=True, required=False)
    images       = ProductImageSerializer(many=True, read_only=True)
    store_name   = serializers.CharField(source='store.name', read_only=True)
    store_id     = serializers.UUIDField(source='store.id', read_only=True)
    distance_km  = serializers.SerializerMethodField(read_only=True)
    is_wishlisted = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = Product
        fields = [
            'id', 'store_id', 'store_name',
            'name', 'description', 'category',
            'status', 'is_visible', 'base_price',
            'variants', 'images',
            'distance_km', 'is_wishlisted',
            'created_at', 'last_updated_at',
        ]
        read_only_fields = ['id', 'store_id', 'store_name', 'created_at', 'last_updated_at']

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_is_wishlisted(self, obj):
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
    store_name  = serializers.CharField(source='store.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    min_price   = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id', 'store_name', 'name', 'category',
            'base_price', 'min_price', 'primary_image',
            'distance_km', 'status',
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        return img.image_url if img else None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None

    @extend_schema_field(serializers.CharField())
    def get_min_price(self, obj):
        variant = obj.variants.order_by('price').first()
        return str(variant.price) if variant else str(obj.base_price)
