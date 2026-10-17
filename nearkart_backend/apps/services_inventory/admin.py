from django.contrib import admin
from .models import Consumable, ServiceConsumable, Equipment, MaintenanceRecord, Resource, ResourceAllocation

admin.site.register(Consumable)
admin.site.register(ServiceConsumable)
admin.site.register(Equipment)
admin.site.register(MaintenanceRecord)
admin.site.register(Resource)
admin.site.register(ResourceAllocation)
