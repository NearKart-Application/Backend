"""
NearKart — Reservation Serializers
"""
from rest_framework import serializers

from apps.products.models import Product
from .models import Reservation, ReservationStatus


class ReservationCreateSerializer(serializers.Serializer):
    store_id         = serializers.UUIDField()
    product_id       = serializers.UUIDField()
    variant_id       = serializers.UUIDField(required=False, allow_null=True, default=None)
    quantity         = serializers.IntegerField(min_value=1, max_value=100, default=1)
    note             = serializers.CharField(max_length=500, allow_blank=True, default='')
    points_to_redeem = serializers.IntegerField(min_value=0, default=0, required=False)
    hours            = serializers.IntegerField(min_value=1, max_value=3, default=2, required=False)
    pickup_time      = serializers.DateTimeField(required=False, allow_null=True, default=None)


class ReservationStatusUpdateSerializer(serializers.Serializer):
    STATUS_CHOICES = [
        ReservationStatus.CONFIRMED,
        ReservationStatus.CANCELLED,
        ReservationStatus.COMPLETED,
    ]
    status                = serializers.ChoiceField(choices=STATUS_CHOICES)
    vendor_note           = serializers.CharField(max_length=500, allow_blank=True, default='')
    actual_selling_price  = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, default=None)
    payment_method        = serializers.ChoiceField(
        choices=['', 'cash', 'upi', 'card', 'credit', 'other'],
        required=False, allow_blank=True, default='',
    )


class ReservationProductSerializer(serializers.Serializer):
    id         = serializers.UUIDField()
    name       = serializers.CharField()
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class ReservationStoreSerializer(serializers.Serializer):
    id       = serializers.UUIDField()
    name     = serializers.CharField()
    locality = serializers.CharField()
    phone    = serializers.CharField()


class ReservationCustomerSerializer(serializers.Serializer):
    id           = serializers.UUIDField()
    phone_number = serializers.CharField()
    full_name    = serializers.CharField()


class ReservationSerializer(serializers.ModelSerializer):
    product      = ReservationProductSerializer(read_only=True)
    store        = ReservationStoreSerializer(read_only=True)
    customer     = ReservationCustomerSerializer(read_only=True)
    hours_left   = serializers.FloatField(read_only=True)
    variant_id   = serializers.UUIDField(source='variant.id',   read_only=True, allow_null=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True, allow_null=True)

    class Meta:
        model  = Reservation
        fields = [
            'id', 'store', 'customer', 'product',
            'variant_id', 'variant_name',
            'quantity', 'note', 'vendor_note',
            'status', 'cancelled_by', 'expires_at', 'hours_left',
            'points_redeemed', 'discount_amount',
            'actual_selling_price', 'payment_method',
            'pickup_time', 'created_at', 'updated_at',
        ]
