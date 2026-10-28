"""
NearKart — Blacklist Serializers
"""
from rest_framework import serializers
from .models import Blacklist


class BlacklistSerializer(serializers.ModelSerializer):
    # customer_id is the customer's USER id — needed for the block/unblock URL
    # (/blacklist/<customer_id>/). 'id' is the blacklist row id and must not be used there.
    customer_id    = serializers.UUIDField(source='customer.id', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    customer_name  = serializers.CharField(source='customer.full_name',    read_only=True)

    class Meta:
        model  = Blacklist
        fields = ['id', 'customer_id', 'customer_phone', 'customer_name', 'reason', 'created_at']
        read_only_fields = ['id', 'customer_id', 'customer_phone', 'customer_name', 'created_at']
