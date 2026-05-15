"""
NearKart — Store Serializers
"""
from rest_framework import serializers
from .models import Store, StoreHours, StoreFollow, StoreReview


class StoreHoursSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_display', read_only=True)

    class Meta:
        model  = StoreHours
        fields = ['day', 'day_name', 'open_time', 'close_time', 'is_closed']


class StoreSerializer(serializers.ModelSerializer):
    latitude      = serializers.FloatField(write_only=True, min_value=-90,  max_value=90)
    longitude     = serializers.FloatField(write_only=True, min_value=-180, max_value=180)
    lat           = serializers.SerializerMethodField(read_only=True)
    lng           = serializers.SerializerMethodField(read_only=True)
    owner_phone   = serializers.CharField(source='owner.phone_number', read_only=True)
    follower_count = serializers.SerializerMethodField(read_only=True)
    hours         = StoreHoursSerializer(many=True, read_only=True)
    distance_km   = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = Store
        fields = [
            'id', 'owner_phone', 'name', 'description', 'category',
            'phone', 'address', 'locality',
            'latitude', 'longitude', 'lat', 'lng',
            'logo_url', 'banner_url', 'qr_code_url',
            'is_active', 'is_verified', 'is_open',
            'performance_score', 'follower_count',
            'hours', 'distance_km', 'created_at',
        ]
        read_only_fields = [
            'id', 'owner_phone', 'is_verified', 'performance_score',
            'qr_code_url', 'locality', 'created_at',
        ]

    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_lng(self, obj):
        return obj.location.x if obj.location else None

    def get_follower_count(self, obj):
        return obj.followers.count()

    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None


class StoreListSerializer(serializers.ModelSerializer):
    """Compact serializer for list/nearby endpoints."""
    lat          = serializers.SerializerMethodField()
    lng          = serializers.SerializerMethodField()
    distance_km  = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = [
            'id', 'name', 'category', 'locality',
            'logo_url', 'is_open', 'is_verified',
            'performance_score', 'lat', 'lng', 'distance_km',
        ]

    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_lng(self, obj):
        return obj.location.x if obj.location else None

    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None


class StoreReviewSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model  = StoreReview
        fields = ['id', 'user_phone', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'user_phone', 'created_at']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value
