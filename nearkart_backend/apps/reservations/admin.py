from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display  = ['id', 'customer', 'store', 'product', 'quantity', 'status', 'expires_at', 'created_at']
    list_filter   = ['status']
    search_fields = ['customer__phone_number', 'store__name', 'product__name']
    readonly_fields = ['id', 'expires_at', 'created_at', 'updated_at']
    ordering      = ['-created_at']
