"""
NearKart — Store Serializers
"""
from django.db import models
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Store, StoreHours, StoreFollow, StoreReview, StoreOffer, Invoice, StaffMember


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
            'id', 'owner_phone', 'name', 'description', 'category', 'store_type',
            'phone', 'address', 'locality',
            'latitude', 'longitude', 'lat', 'lng',
            'logo_url', 'banner_url', 'qr_code_url',
            'is_active', 'is_verified', 'is_open', 'is_women_owned',
            'privacy_mode', 'holiday_mode',
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
    avatar            = serializers.URLField(source='logo_url', read_only=True)
    cover_image       = serializers.URLField(source='banner_url', read_only=True)
    location          = serializers.CharField(source='locality', read_only=True)
    lat               = serializers.SerializerMethodField()
    lng               = serializers.SerializerMethodField()
    distance_km       = serializers.SerializerMethodField()
    rating            = serializers.SerializerMethodField()
    review_count      = serializers.SerializerMethodField()
    follower_count    = serializers.SerializerMethodField()
    has_offer           = serializers.SerializerMethodField()
    top_offer_label     = serializers.SerializerMethodField()
    active_offer_labels = serializers.SerializerMethodField()
    open_status_label   = serializers.SerializerMethodField()
    todays_hours      = serializers.SerializerMethodField()
    top_subcategories = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = [
            'id', 'name', 'category', 'locality', 'location',
            'avatar', 'cover_image', 'is_open', 'is_verified',
            'holiday_mode',
            'performance_score', 'lat', 'lng', 'distance_km',
            'rating', 'review_count', 'follower_count',
            'has_offer', 'top_offer_label', 'active_offer_labels', 'open_status_label', 'todays_hours',
            'top_subcategories',
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

    @extend_schema_field(serializers.FloatField())
    def get_rating(self, obj):
        # Uses annotated avg_rating from get_nearby_stores queryset — zero DB hit
        avg = getattr(obj, 'avg_rating', None)
        return round(float(avg), 1) if avg else 0.0

    @extend_schema_field(serializers.IntegerField())
    def get_review_count(self, obj):
        return getattr(obj, 'review_count_ann', None) or 0

    @extend_schema_field(serializers.IntegerField())
    def get_follower_count(self, obj):
        return getattr(obj, 'follower_count', None) or 0

    @extend_schema_field(serializers.BooleanField())
    def get_has_offer(self, obj):
        # Uses prefetched active offers — zero DB hit
        return any(True for _ in obj.offers.all())

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_top_offer_label(self, obj):
        # Uses prefetched active offers sorted by -created_at — zero DB hit
        offer = next(iter(obj.offers.all()), None)
        if not offer:
            return None
        label = offer.title
        if offer.discount_pct:
            label += f' · {offer.discount_pct}% off'
        return label

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_active_offer_labels(self, obj):
        # Latest 5 active non-expired offers — uses prefetched queryset, zero DB hit
        labels = []
        for offer in obj.offers.all():
            if len(labels) >= 5:
                break
            label = offer.title
            if offer.discount_pct:
                label += f' · {offer.discount_pct}% off'
            labels.append(label)
        return labels

    @extend_schema_field(serializers.CharField())
    def get_open_status_label(self, obj):
        if obj.is_open:
            from datetime import date
            day = date.today().weekday()
            # Uses prefetched non-closed hours — zero DB hit
            hours = next((h for h in obj.hours.all() if h.day == day), None)
            if hours:
                return f'Closes {hours.close_time.strftime("%-I:%M %p")}'
            return 'Open now'
        return 'Closed'

    @extend_schema_field(serializers.CharField())
    def get_todays_hours(self, obj):
        from datetime import date
        day = date.today().weekday()
        # Uses prefetched non-closed hours — zero DB hit
        hours = next((h for h in obj.hours.all() if h.day == day), None)
        if hours:
            return f'{hours.open_time.strftime("%-I %p")}–{hours.close_time.strftime("%-I %p")}'
        return ''

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_top_subcategories(self, obj):
        return list(
            obj.products.filter(status='active', is_visible=True)
            .exclude(subcategory='')
            .values_list('subcategory', flat=True)
            .distinct()[:4]
        )


class StoreReviewSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model  = StoreReview
        fields = ['id', 'user_phone', 'rating', 'comment', 'is_verified', 'vendor_reply', 'vendor_reply_at', 'created_at']
        read_only_fields = ['id', 'user_phone', 'is_verified', 'vendor_reply', 'vendor_reply_at', 'created_at']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value


class StoreReviewListSerializer(serializers.ModelSerializer):
    """Read-only review for public list endpoint — shows user initials instead of phone."""
    user_name = serializers.SerializerMethodField()

    class Meta:
        model  = StoreReview
        fields = ['id', 'user_name', 'rating', 'comment', 'is_verified', 'vendor_reply', 'vendor_reply_at', 'created_at']

    @extend_schema_field(serializers.CharField())
    def get_user_name(self, obj):
        name = getattr(obj.user, 'full_name', '') or ''
        if name:
            parts = name.split()
            return f'{parts[0]} {"*" * (len(parts[1]) if len(parts) > 1 else 0)}'.strip()
        phone = obj.user.phone_number or ''
        return phone[:4] + '****' + phone[-2:] if len(phone) >= 6 else '****'


class VendorReplySerializer(serializers.Serializer):
    reply = serializers.CharField(min_length=1, max_length=1000)


class StoreOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StoreOffer
        fields = ['id', 'title', 'description', 'discount_pct', 'valid_till', 'image_url', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


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
        # Uses annotated follower_count if available, falls back to DB count
        return getattr(obj, 'follower_count', None) or obj.followers.count()

    @extend_schema_field(serializers.BooleanField())
    def get_is_followed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.followers.filter(user=request.user).exists()
        return False

    @extend_schema_field(serializers.FloatField())
    def get_rating(self, obj):
        avg = getattr(obj, 'avg_rating', None)
        return round(float(avg), 1) if avg else 0.0

    @extend_schema_field(serializers.IntegerField())
    def get_review_count(self, obj):
        return getattr(obj, 'review_count_ann', None) or obj.reviews.count()

    @extend_schema_field(serializers.CharField())
    def get_open_status_label(self, obj):
        if obj.is_open:
            from datetime import date
            day = date.today().weekday()
            hours = next((h for h in obj.hours.all() if h.day == day and not h.is_closed), None)
            if hours:
                return f'Open · Closes at {hours.close_time.strftime("%I:%M %p")}'
            return 'Open'
        return 'Closed'

    @extend_schema_field(serializers.CharField())
    def get_todays_hours(self, obj):
        from datetime import date
        day = date.today().weekday()
        hours = next((h for h in obj.hours.all() if h.day == day and not h.is_closed), None)
        if hours:
            return f'{hours.open_time.strftime("%H:%M")}-{hours.close_time.strftime("%H:%M")}'
        return ''

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_closes_at(self, obj):
        from datetime import date
        day = date.today().weekday()
        hours = next((h for h in obj.hours.all() if h.day == day and not h.is_closed), None)
        return hours.close_time.strftime('%H:%M') if hours else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_next_open(self, obj):
        return None


class InvoiceSerializer(serializers.ModelSerializer):
    gst_amount = serializers.SerializerMethodField()

    def get_gst_amount(self, obj):
        from decimal import Decimal
        if obj.gst_rate and obj.gst_rate > 0:
            return round(float(obj.total) * float(obj.gst_rate) / 100, 2)
        return 0.0

    class Meta:
        model  = Invoice
        fields = [
            'id', 'customer_name', 'customer_phone', 'customer_ns_code',
            'items', 'notes', 'total', 'is_sent', 'created_at',
            'discount_type', 'discount_value',
            'gstin', 'gst_rate', 'gst_amount',
        ]
        read_only_fields = ['id', 'total', 'created_at', 'is_sent', 'gst_amount']


class CustomerInvoiceSerializer(serializers.ModelSerializer):
    """Invoice as seen by the customer — includes store info for the Purchase History screen."""
    store_id    = serializers.UUIDField(source='store.id', read_only=True)
    store_name  = serializers.CharField(source='store.name', read_only=True)
    store_logo  = serializers.URLField(source='store.logo_url', read_only=True)
    store_address = serializers.CharField(source='store.address', read_only=True)
    store_phone = serializers.CharField(source='store.phone', read_only=True)
    gst_amount  = serializers.SerializerMethodField()

    def get_gst_amount(self, obj):
        if obj.gst_rate and obj.gst_rate > 0:
            return round(float(obj.total) * float(obj.gst_rate) / 100, 2)
        return 0.0

    class Meta:
        model  = Invoice
        fields = [
            'id', 'store_id', 'store_name', 'store_logo', 'store_address', 'store_phone',
            'customer_name', 'customer_phone', 'customer_ns_code',
            'items', 'notes', 'total',
            'discount_type', 'discount_value',
            'gstin', 'gst_rate', 'gst_amount',
            'is_sent', 'created_at',
        ]
        read_only_fields = fields


class StoreFollowerSerializer(serializers.Serializer):
    full_name  = serializers.SerializerMethodField()
    profile_id = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.user.full_name or 'NearKart User'

    def get_profile_id(self, obj):
        return obj.user.profile_id or ''


class StaffMemberSerializer(serializers.ModelSerializer):
    name       = serializers.SerializerMethodField()
    phone      = serializers.SerializerMethodField()
    profile_id = serializers.SerializerMethodField()

    class Meta:
        model  = StaffMember
        fields = ['id', 'name', 'phone', 'profile_id', 'role', 'is_active', 'created_at']
        read_only_fields = ['id', 'name', 'phone', 'profile_id', 'created_at']

    def get_name(self, obj):
        return obj.user.full_name or ''

    def get_phone(self, obj):
        return obj.user.phone_number

    def get_profile_id(self, obj):
        return obj.user.profile_id
