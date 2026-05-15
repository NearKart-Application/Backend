"""
NearKart — Video Serializers
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Video


class VideoSerializer(serializers.ModelSerializer):
    store_name  = serializers.CharField(source='store.name', read_only=True)
    store_id    = serializers.UUIDField(source='store.id', read_only=True)
    distance_km = serializers.SerializerMethodField()
    is_liked    = serializers.SerializerMethodField()

    class Meta:
        model  = Video
        fields = [
            'id', 'store_id', 'store_name',
            'title', 'description',
            'video_url', 'thumbnail_url',
            'status', 'duration_seconds',
            'view_count', 'like_count', 'is_liked',
            'locality', 'distance_km',
            'is_visible', 'expires_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'store_id', 'store_name',
            'video_url', 'thumbnail_url', 'status',
            'view_count', 'like_count',
            'locality', 'expires_at',
            'created_at', 'updated_at',
        ]

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


class VideoUploadRequestSerializer(serializers.Serializer):
    title       = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
