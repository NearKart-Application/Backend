"""
NearKart — Blacklist Admin
Shopify-grade admin for Blacklist (vendor blocks a customer from their store).
"""
from django.contrib import admin

from .models import Blacklist


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display    = ['store', 'customer_phone', 'reason', 'created_at']
    list_filter     = ['store']
    search_fields   = ['store__name', 'customer__phone_number', 'reason']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    show_full_result_count = False
    list_select_related    = ['store', 'customer']
    raw_id_fields   = ['store', 'customer']
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='Customer', ordering='customer__phone_number')
    def customer_phone(self, obj):
        return obj.customer.phone_number
