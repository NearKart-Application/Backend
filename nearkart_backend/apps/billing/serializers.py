"""
NearKart — Billing Serializers
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Plan, Subscription, Transaction


class PlanSerializer(serializers.ModelSerializer):
    video_limit_display   = serializers.SerializerMethodField()
    product_limit_display = serializers.SerializerMethodField()

    class Meta:
        model  = Plan
        fields = [
            'id', 'name', 'display_name', 'price', 'duration_days',
            'video_limit', 'product_limit',
            'video_limit_display', 'product_limit_display',
            'description',
        ]

    @extend_schema_field(serializers.CharField())
    def get_video_limit_display(self, obj):
        return 'Unlimited' if obj.video_limit == 0 else str(obj.video_limit)

    @extend_schema_field(serializers.CharField())
    def get_product_limit_display(self, obj):
        return 'Unlimited' if obj.product_limit == 0 else str(obj.product_limit)


class SubscriptionSerializer(serializers.ModelSerializer):
    plan         = PlanSerializer(read_only=True)
    days_left    = serializers.SerializerMethodField()
    store_name   = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model  = Subscription
        fields = [
            'id', 'store_name', 'plan',
            'started_at', 'expires_at', 'is_active', 'days_left',
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_days_left(self, obj):
        from django.utils import timezone
        if not obj.is_active:
            return 0
        delta = obj.expires_at - timezone.now()
        return max(0, delta.days)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Transaction
        fields = [
            'id', 'type', 'amount', 'description',
            'reference_id', 'balance_after', 'created_at',
        ]
