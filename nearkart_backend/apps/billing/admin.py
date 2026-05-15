from django.contrib import admin
from .models import Plan, Subscription, Transaction


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display  = ['display_name', 'price', 'duration_days', 'video_limit', 'product_limit', 'is_active']
    list_editable = ['is_active']
    ordering      = ['price']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ['store', 'plan', 'started_at', 'expires_at', 'is_active']
    list_filter   = ['plan', 'is_active']
    search_fields = ['store__name', 'store__owner__phone_number']
    ordering      = ['-expires_at']
    raw_id_fields = ['store', 'plan']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display  = ['store', 'type', 'amount', 'balance_after', 'description', 'created_at']
    list_filter   = ['type']
    search_fields = ['store__name', 'reference_id', 'description']
    ordering      = ['-created_at']
    raw_id_fields = ['store']
