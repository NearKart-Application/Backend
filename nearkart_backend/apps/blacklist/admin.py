from django.contrib import admin
from .models import Blacklist


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display  = ['store', 'customer', 'reason', 'created_at']
    list_filter   = ['store']
    search_fields = ['store__name', 'customer__phone_number', 'reason']
    raw_id_fields = ['store', 'customer']
    ordering      = ['-created_at']
