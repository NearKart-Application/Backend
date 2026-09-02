from rest_framework import serializers
from .models import Consumable, ServiceConsumable, Equipment, MaintenanceRecord, Resource, ResourceAllocation


class ConsumableSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model  = Consumable
        fields = ['id', 'name', 'unit', 'current_stock', 'reorder_level', 'cost_per_unit', 'notes', 'is_low_stock', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_is_low_stock(self, obj):
        return obj.is_low_stock


class ServiceConsumableSerializer(serializers.ModelSerializer):
    consumable_name = serializers.CharField(source='consumable.name', read_only=True)
    unit            = serializers.CharField(source='consumable.unit', read_only=True)

    class Meta:
        model  = ServiceConsumable
        fields = ['id', 'consumable', 'consumable_name', 'unit', 'quantity_per_session', 'notes']
        read_only_fields = ['id']


class EquipmentSerializer(serializers.ModelSerializer):
    is_maintenance_due = serializers.SerializerMethodField()

    class Meta:
        model  = Equipment
        fields = [
            'id', 'name', 'serial_number', 'purchase_date',
            'last_maintenance_date', 'next_maintenance_date',
            'maintenance_interval_days', 'condition', 'notes',
            'is_maintenance_due', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_is_maintenance_due(self, obj):
        return obj.is_maintenance_due


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)

    class Meta:
        model  = MaintenanceRecord
        fields = ['id', 'equipment', 'equipment_name', 'date', 'performed_by', 'cost', 'description', 'next_due', 'created_at']
        read_only_fields = ['id', 'created_at']


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Resource
        fields = ['id', 'name', 'resource_type', 'capacity', 'is_active', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class ResourceAllocationSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source='resource.name', read_only=True)

    class Meta:
        model  = ResourceAllocation
        fields = ['id', 'resource', 'resource_name', 'reservation', 'staff_name', 'date', 'start_time', 'end_time', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']
