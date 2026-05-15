"""
NearKart — Reservation Serializers
"""
from rest_framework import serializers

from apps.products.models import Product
from .models import Reservation, ReservationStatus


class ReservationCreateSerializer(serializers.Serializer):
    store_id   = serializers.UUIDField()
    product_id = serializers.UUIDField()
    quantity   = serializers.IntegerField(min_value=1, max_value=100, default=1)
    note       = serializers.CharField(max_length=500, allow_blank=True, default='')


class ReservationStatusUpdateSerializer(serializers.Serializer):
    STATUS_CHOICES = [
        ReservationStatus.CONFIRMED,
        ReservationStatus.CANCELLED,
        ReservationStatus.COMPLETED,
    ]
    status      = serializers.ChoiceField(choices=STATUS_CHOICES)
    vendor_note = serializers.CharField(max_length=500, allow_blank=True, default='')


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
    product  = ReservationProductSerializer(read_only=True)
    store    = ReservationStoreSerializer(read_only=True)
    customer = ReservationCustomerSerializer(read_only=True)
    hours_left = serializers.FloatField(read_only=True)

    class Meta:
        model  = Reservation
        fields = [
            'id', 'store', 'customer', 'product',
            'quantity', 'note', 'vendor_note',
            'status', 'expires_at', 'hours_left',
            'created_at', 'updated_at',
        ]
