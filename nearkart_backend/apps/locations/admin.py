from django.contrib import admin
from .models import LocationMaster


@admin.register(LocationMaster)
class LocationMasterAdmin(admin.ModelAdmin):
    list_display  = ['state', 'district', 'city']
    list_filter   = ['state']
    search_fields = ['state', 'district', 'city']
    list_per_page = 50
    ordering      = ['state', 'district', 'city']
