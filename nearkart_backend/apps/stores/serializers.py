"""
NearKart — Store Serializers
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
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

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_lng(self, obj):
        return obj.location.x if obj.location else None

    @extend_schema_field(serializers.IntegerField())
    def get_follower_count(self, obj):
        return obj.followers.count()

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return None


class StoreListSerializer(serializers.ModelSerializer):
    """Compact serializer for list/nearby endpoints — mobile-compatible field names."""
    avatar       = serializers.URLField(source='logo_url', read_only=True)
    cover_image  = serializers.URLField(source='banner_url', read_only=True)
    lat          = serializers.SerializerMethodField()
    lng          = serializers.SerializerMethodField()
    distance_km  = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = [
            'id', 'name', 'category', 'locality',
            'avatar', 'cover_image', 'is_open', 'is_verified',
            'performance_score', 'lat', 'lng', 'distance_km',
        ]

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_lng(self, obj):
        return obj.location.x if obj.location else None

    @extend_schema_field(serializers.FloatField(allow_null=True))
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


class StoreMobileDetailSerializer(serializers.ModelSerializer):
    """Mobile-compatible store detail serializer (C9 screen)."""
    avatar           = serializers.URLField(source='logo_url', read_only=True)
    cover_image      = serializers.URLField(source='banner_url', read_only=True)
    location         = serializers.CharField(source='locality', read_only=True)
    distance_km      = serializers.SerializerMethodField()
    follower_count   = serializers.SerializerMethodField()
    is_followed      = serializers.SerializerMethodField()
    rating           = serializers.SerializerMethodField()
    review_count     = serializers.SerializerMethodField()
    open_status_label = serializers.SerializerMethodField()
    todays_hours     = serializers.SerializerMethodField()
    closes_at        = serializers.SerializerMethodField()
    next_open        = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = [
            'id', 'name', 'avatar', 'cover_image', 'category',
            'location', 'distance_km',
            'is_open', 'open_status_label', 'todays_hours', 'closes_at', 'next_open',
            'rating', 'review_count', 'follower_count', 'is_followed',
        ]

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.km, 2)
        return 0.0

    @extend_schema_field(serializers.IntegerField())
    def get_follower_count(self, obj):
        return obj.followers.count()

    @extend_schema_field(serializers.BooleanField())
    def get_is_followed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.followers.filter(user=request.user).exists()
        return False

    @extend_schema_field(serializers.FloatField())
    def get_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews.exists():
            return 0.0
        total = sum(r.rating for r in reviews)
        return round(total / reviews.count(), 1)

    @extend_schema_field(serializers.IntegerField())
    def get_review_count(self, obj):
        return obj.reviews.count()

    @extend_schema_field(serializers.CharField())
    def get_open_status_label(self, obj):
        if obj.is_open:
            hours = obj.hours.filter(is_closed=False).first()
            if hours:
                return f'Open · Closes at {hours.close_time.strftime("%I:%M %p")}'
            return 'Open'
        return 'Closed'

    @extend_schema_field(serializers.CharField())
    def get_todays_hours(self, obj):
        from datetime import date
        day = date.today().weekday()
        hours = obj.hours.filter(day=day, is_closed=False).first()
        if hours:
            return f'{hours.open_time.strftime("%H:%M")}-{hours.close_time.strftime("%H:%M")}'
        return ''

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_closes_at(self, obj):
        from datetime import date
        day = date.today().weekday()
        hours = obj.hours.filter(day=day, is_closed=False).first()
        return hours.close_time.strftime('%H:%M') if hours else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_next_open(self, obj):
        return None
