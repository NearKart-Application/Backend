"""
NearKart — Video Serializers
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Video, VideoProductTag


class StoreMiniSerializer(serializers.Serializer):
    id     = serializers.UUIDField(source='store.id', read_only=True)
    name   = serializers.CharField(source='store.name', read_only=True)
    avatar = serializers.URLField(source='store.logo_url', read_only=True)


class VideoProductTagSerializer(serializers.ModelSerializer):
    id    = serializers.UUIDField(read_only=True)
    name  = serializers.CharField(source='product.name', read_only=True)
    price = serializers.DecimalField(source='product.base_price', max_digits=10,
                                     decimal_places=2, read_only=True)

    class Meta:
        model  = VideoProductTag
        fields = ['id', 'name', 'price', 'x_pct', 'y_pct']


class VideoProductTagWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = VideoProductTag
        fields = ['product', 'x_pct', 'y_pct']

    def validate_x_pct(self, v):
        if not 0.0 <= v <= 1.0:
            raise serializers.ValidationError('x_pct must be between 0.0 and 1.0')
        return v

    def validate_y_pct(self, v):
        if not 0.0 <= v <= 1.0:
            raise serializers.ValidationError('y_pct must be between 0.0 and 1.0')
        return v


class VideoSerializer(serializers.ModelSerializer):
    # Flat legacy fields kept for admin/vendor API consumers
    store_id    = serializers.UUIDField(source='store.id', read_only=True)
    store_name  = serializers.CharField(source='store.name', read_only=True)

    # Mobile-expected nested store object
    store       = serializers.SerializerMethodField()

    # Mobile-expected field aliases
    hls_url     = serializers.CharField(source='video_url', read_only=True)
    thumbnail   = serializers.CharField(source='thumbnail_url', read_only=True)
    duration    = serializers.IntegerField(source='duration_seconds', read_only=True)

    distance_km = serializers.SerializerMethodField()
    is_liked    = serializers.SerializerMethodField()
    is_saved    = serializers.SerializerMethodField()
    tags        = serializers.SerializerMethodField()

    product_id = serializers.UUIDField(source='product.id', read_only=True, allow_null=True)

    class Meta:
        model  = Video
        fields = [
            'id',
            'store_id', 'store_name',   # flat (legacy / admin)
            'store',                     # nested (mobile)
            'title', 'description',
            'video_type', 'product_id',
            'video_url', 'thumbnail_url',   # original names
            'hls_url', 'thumbnail',         # mobile aliases
            'status',
            'duration_seconds', 'duration', # original + mobile alias
            'view_count', 'like_count', 'is_liked', 'is_saved',
            'locality', 'distance_km',
            'is_visible', 'expires_at',
            'tags',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'store_id', 'store_name',
            'video_url', 'thumbnail_url', 'status',
            'view_count', 'like_count',
            'locality', 'expires_at',
            'created_at', 'updated_at',
        ]

    @extend_schema_field(serializers.DictField())
    def get_store(self, obj):
        return {
            'id':     str(obj.store_id),
            'name':   obj.store.name,
            'avatar': obj.store.logo_url or None,
        }

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    @extend_schema_field(serializers.BooleanField())
    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.saves.filter(user=request.user).exists()
        return False

    @extend_schema_field(VideoProductTagSerializer(many=True))
    def get_tags(self, obj):
        tags = obj.product_tags.select_related('product').all()
        return VideoProductTagSerializer(tags, many=True).data


class VideoUploadRequestSerializer(serializers.Serializer):
    title       = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    video_type  = serializers.ChoiceField(choices=['store_promo', 'product_demo'], default='store_promo')
    product_id  = serializers.UUIDField(required=False, allow_null=True, default=None)
