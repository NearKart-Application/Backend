"""
NearKart — Services Inventory models (#147–#150)

Consumables: track supplies used per service session (shampoo, chemicals, parts)
ServiceConsumable: links a ServiceCatalogue item to consumables + qty per session
Equipment: tools / machinery with maintenance scheduling
MaintenanceRecord: log of maintenance events for equipment
Resource: chairs, bays, rooms, or other bookable units
ResourceAllocation: time-blocked allocation of a resource (linked to reservation or manual)
"""
from datetime import date
from django.db import models
from core.models import BaseModel


class ConsumableUnit(models.TextChoices):
    ML     = 'ml',     'Millilitre'
    LITRE  = 'litre',  'Litre'
    GRAM   = 'gram',   'Gram'
    KG     = 'kg',     'Kilogram'
    PIECE  = 'piece',  'Piece'
    BOTTLE = 'bottle', 'Bottle'
    SACHET = 'sachet', 'Sachet'
    PAIR   = 'pair',   'Pair'


class Consumable(BaseModel):
    store         = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='consumables')
    name          = models.CharField(max_length=100)
    unit          = models.CharField(max_length=20, choices=ConsumableUnit.choices, default=ConsumableUnit.PIECE)
    current_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes         = models.TextField(blank=True)

    class Meta:
        db_table  = 'svc_consumables'
        ordering  = ['name']
        indexes   = [models.Index(fields=['store', 'name'], name='svc_cons_store_name_idx')]

    def __str__(self):
        return f'{self.name} ({self.unit})'

    @property
    def is_low_stock(self):
        return self.current_stock <= self.reorder_level


class ServiceConsumable(BaseModel):
    """Links a ServiceCatalogue item to a consumable with quantity-per-session."""
    service           = models.ForeignKey('stores.ServiceCatalogue', on_delete=models.CASCADE, related_name='consumables')
    consumable        = models.ForeignKey(Consumable, on_delete=models.CASCADE, related_name='service_links')
    quantity_per_session = models.DecimalField(max_digits=10, decimal_places=3)
    notes             = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table       = 'svc_service_consumables'
        unique_together = ('service', 'consumable')

    def __str__(self):
        return f'{self.service} uses {self.quantity_per_session} {self.consumable.unit} of {self.consumable}'


class EquipmentCondition(models.TextChoices):
    GOOD         = 'good',         'Good'
    FAIR         = 'fair',         'Fair'
    NEEDS_REPAIR = 'needs_repair', 'Needs Repair'
    OUT_OF_SERVICE = 'out_of_service', 'Out of Service'


class Equipment(BaseModel):
    store                    = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='equipment')
    name                     = models.CharField(max_length=100)
    serial_number            = models.CharField(max_length=100, blank=True)
    purchase_date            = models.DateField(null=True, blank=True)
    last_maintenance_date    = models.DateField(null=True, blank=True)
    next_maintenance_date    = models.DateField(null=True, blank=True)
    maintenance_interval_days = models.PositiveIntegerField(null=True, blank=True, help_text='Days between scheduled maintenance')
    condition                = models.CharField(max_length=20, choices=EquipmentCondition.choices, default=EquipmentCondition.GOOD)
    notes                    = models.TextField(blank=True)

    class Meta:
        db_table = 'svc_equipment'
        ordering = ['name']
        indexes  = [models.Index(fields=['store', 'condition'], name='svc_equip_store_cond_idx')]

    def __str__(self):
        return self.name

    @property
    def is_maintenance_due(self):
        return bool(self.next_maintenance_date and self.next_maintenance_date <= date.today())


class MaintenanceRecord(BaseModel):
    equipment    = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenance_records')
    date         = models.DateField()
    performed_by = models.CharField(max_length=200, blank=True)
    cost         = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description  = models.TextField()
    next_due     = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'svc_maintenance_records'
        ordering = ['-date']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep equipment's last/next maintenance dates in sync
        eq = self.equipment
        if not eq.last_maintenance_date or self.date >= eq.last_maintenance_date:
            eq.last_maintenance_date = self.date
            if self.next_due:
                eq.next_maintenance_date = self.next_due
            eq.save(update_fields=['last_maintenance_date', 'next_maintenance_date'])


class ResourceType(models.TextChoices):
    CHAIR = 'chair', 'Chair'
    BAY   = 'bay',   'Bay'
    ROOM  = 'room',  'Room'
    TABLE = 'table', 'Table'
    OTHER = 'other', 'Other'


class Resource(BaseModel):
    store         = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='resources')
    name          = models.CharField(max_length=100, help_text='e.g. Chair 1, Bay A, Treatment Room 2')
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices, default=ResourceType.CHAIR)
    capacity      = models.PositiveIntegerField(default=1)
    is_active     = models.BooleanField(default=True)
    notes         = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'svc_resources'
        ordering = ['resource_type', 'name']

    def __str__(self):
        return f'{self.name} ({self.resource_type})'


class ResourceAllocation(BaseModel):
    resource    = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='allocations')
    reservation = models.ForeignKey('reservations.Reservation', null=True, blank=True, on_delete=models.SET_NULL, related_name='resource_allocations')
    staff_name  = models.CharField(max_length=100, blank=True)
    date        = models.DateField()
    start_time  = models.TimeField()
    end_time    = models.TimeField()
    notes       = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'svc_resource_allocations'
        ordering = ['date', 'start_time']
        indexes  = [models.Index(fields=['resource', 'date'], name='svc_alloc_res_date_idx')]
