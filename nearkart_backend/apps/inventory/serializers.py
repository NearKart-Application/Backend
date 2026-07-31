"""Nearspot — Inventory Serializers"""
from rest_framework import serializers
from .models import Supplier, PurchaseOrder, StockAudit, CompositeProduct, SerialNumber
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


class CompositeProductSerializer(serializers.ModelSerializer):
    bundle_product_name    = serializers.CharField(source='bundle_product.name', read_only=True)
    component_variant_name = serializers.CharField(source='component_variant.name', read_only=True)
    component_sku          = serializers.CharField(source='component_variant.sku', read_only=True)

    class Meta:
        model  = CompositeProduct
        fields = [
            'id', 'bundle_product', 'bundle_product_name',
            'component_variant', 'component_variant_name', 'component_sku',
            'quantity', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class SerialNumberSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    variant_sku  = serializers.CharField(source='variant.sku', read_only=True)

    class Meta:
        model  = SerialNumber
        fields = [
            'id', 'variant', 'variant_name', 'variant_sku',
            'serial_number', 'status', 'sold_at', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
