"""Nearspot — Inventory Serializers"""
from rest_framework import serializers
from .models import Supplier, PurchaseOrder, StockAudit
# StockMovementLog and StockWatchlist live in the products app (canonical tables);
# the inventory.models duplicates are empty shadow tables.
from apps.products.models import StockMovementLog, StockWatchlist


class StockMovementLogSerializer(serializers.ModelSerializer):
    variant_sku  = serializers.CharField(source='variant.sku', read_only=True, default='')
    changed_by_phone = serializers.CharField(source='changed_by.phone_number', read_only=True, default='')

    class Meta:
        model  = StockMovementLog
        fields = [
            'id', 'variant', 'variant_sku', 'changed_by', 'changed_by_phone',
            'old_qty', 'new_qty', 'delta', 'reason', 'note', 'created_at',
        ]
        read_only_fields = fields


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Supplier
        fields = [
            'id', 'store', 'name', 'contact_name', 'phone', 'whatsapp',
            'address', 'product_categories', 'notes', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'store', 'created_at']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default='')

    class Meta:
        model  = PurchaseOrder
        fields = [
            'id', 'store', 'supplier', 'supplier_name', 'status',
            'items', 'total_cost', 'notes', 'expected_by', 'received_at', 'created_at',
        ]
        read_only_fields = ['id', 'store', 'created_at']


class StockAuditSerializer(serializers.ModelSerializer):
    conducted_by_phone = serializers.CharField(
        source='conducted_by.phone_number', read_only=True, default='',
    )

    class Meta:
        model  = StockAudit
        fields = [
            'id', 'store', 'conducted_by', 'conducted_by_phone',
            'status', 'items', 'total_discrepancy', 'notes', 'completed_at', 'created_at',
        ]
        read_only_fields = ['id', 'store', 'conducted_by', 'created_at']


class StockWatchlistSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model  = StockWatchlist
        fields = ['id', 'product', 'product_name', 'notified_at', 'created_at']
        read_only_fields = ['id', 'notified_at', 'created_at']
