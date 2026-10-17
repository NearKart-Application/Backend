"""
NearKart — Inventory Admin
Shopify-grade admin for StockMovementLog, StockWatchlist, Supplier,
PurchaseOrder, StockAudit, CompositeProduct, SerialNumber.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    StockMovementLog, StockWatchlist,
    Supplier, PurchaseOrder,
    StockAudit, CompositeProduct, SerialNumber,
)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _badge(text, bg, color):
    return format_html(
        '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:{};color:{}">{}</span>',
        bg, color, text
    )


# ─── Stock Movement Log (immutable audit trail) ───────────────────────────────

@admin.register(StockMovementLog)
class StockMovementLogAdmin(admin.ModelAdmin):
    list_display    = [
        'variant', 'store_name', 'reason_badge',
        'delta_display', 'old_qty', 'new_qty', 'changed_by', 'created_at',
    ]
    list_filter     = ['reason']
    search_fields   = ['variant__name', 'variant__sku', 'changed_by__phone_number', 'note']
    readonly_fields = [
        'variant', 'changed_by', 'old_qty', 'new_qty',
        'delta', 'reason', 'note', 'created_at', 'updated_at',
    ]
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['variant', 'variant__product',
                               'variant__product__store', 'changed_by']

    @admin.display(description='Store')
    def store_name(self, obj):
        try:
            return obj.variant.product.store.name
        except Exception:
            return '—'

    @admin.display(description='Change', ordering='delta')
    def delta_display(self, obj):
        if obj.delta > 0:
            return format_html('<b style="color:#155724">+{}</b>', obj.delta)
        return format_html('<b style="color:#721c24">{}</b>', obj.delta)

    @admin.display(description='Reason', ordering='reason')
    def reason_badge(self, obj):
        colors = {
            'manual':      ('#e2e3e5', '#383d41'),
            'reservation': ('#f8d7da', '#721c24'),
            'restoration': ('#d4edda', '#155724'),
            'invoice':     ('#cce5ff', '#004085'),
            'purchase':    ('#d4edda', '#155724'),
            'return':      ('#fff3cd', '#856404'),
            'damage':      ('#f8d7da', '#721c24'),
            'correction':  ('#e8d5f0', '#4a235a'),
        }
        bg, color = colors.get(obj.reason, ('#e2e3e5', '#333'))
        return _badge(obj.get_reason_display(), bg, color)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ─── Stock Watchlist ──────────────────────────────────────────────────────────

@admin.register(StockWatchlist)
class StockWatchlistAdmin(admin.ModelAdmin):
    list_display    = ['customer_phone', 'product', 'notified_at', 'created_at']
    search_fields   = ['customer__phone_number', 'product__name']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['customer', 'product']
    raw_id_fields   = ['customer', 'product']
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='Customer', ordering='customer__phone_number')
    def customer_phone(self, obj):
        return obj.customer.phone_number


# ─── Supplier ─────────────────────────────────────────────────────────────────

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display    = [
        'name', 'store', 'contact_name', 'phone',
        'whatsapp', 'product_categories', 'is_active_badge',
    ]
    list_filter     = ['is_active']
    search_fields   = ['name', 'contact_name', 'phone', 'store__name']
    ordering        = ['name']
    list_per_page   = 25
    list_select_related    = ['store']
    raw_id_fields   = ['store']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Supplier Info', {'fields': ('store', 'name', 'contact_name',
                                      'phone', 'whatsapp', 'is_active')}),
        ('Details',       {'fields': ('address', 'product_categories', 'notes')}),
        ('Meta',          {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#e2e3e5', '#383d41')


# ─── Purchase Order ───────────────────────────────────────────────────────────

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display    = [
        'id', 'store', 'supplier', 'status_badge',
        'total_cost', 'expected_by', 'received_at', 'created_at',
    ]
    list_filter     = ['status']
    search_fields   = ['store__name', 'supplier__name']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['store', 'supplier']
    raw_id_fields   = ['store', 'supplier']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Order',   {'fields': ('store', 'supplier', 'status', 'total_cost')}),
        ('Items',   {'fields': ('items',)}),
        ('Dates',   {'fields': ('expected_by', 'received_at', 'created_at', 'updated_at')}),
        ('Notes',   {'fields': ('notes',)}),
    )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'draft':     ('#e2e3e5', '#383d41'),
            'sent':      ('#cce5ff', '#004085'),
            'received':  ('#d4edda', '#155724'),
            'cancelled': ('#f8d7da', '#721c24'),
        }
        bg, color = colors.get(obj.status, ('#e2e3e5', '#333'))
        return _badge(obj.get_status_display(), bg, color)


# ─── Stock Audit ──────────────────────────────────────────────────────────────

@admin.register(StockAudit)
class StockAuditAdmin(admin.ModelAdmin):
    list_display    = [
        'id', 'store', 'conducted_by', 'status_badge',
        'discrepancy_display', 'completed_at', 'created_at',
    ]
    list_filter     = ['status']
    search_fields   = ['store__name', 'conducted_by__phone_number']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['store', 'conducted_by']
    raw_id_fields   = ['store', 'conducted_by']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Audit',  {'fields': ('store', 'conducted_by', 'status', 'total_discrepancy')}),
        ('Items',  {'fields': ('items',)}),
        ('Dates',  {'fields': ('completed_at', 'created_at', 'updated_at')}),
        ('Notes',  {'fields': ('notes',)}),
    )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'in_progress': ('#fff3cd', '#856404'),
            'completed':   ('#d4edda', '#155724'),
            'cancelled':   ('#f8d7da', '#721c24'),
        }
        bg, color = colors.get(obj.status, ('#e2e3e5', '#333'))
        return _badge(obj.get_status_display(), bg, color)

    @admin.display(description='Discrepancy', ordering='total_discrepancy')
    def discrepancy_display(self, obj):
        d = obj.total_discrepancy
        if d == 0:
            return format_html('<span style="color:#155724;font-weight:600">0</span>')
        elif d > 0:
            return format_html('<span style="color:#856404;font-weight:600">+{}</span>', d)
        return format_html('<span style="color:#721c24;font-weight:600">{}</span>', d)


# ─── Composite Product ────────────────────────────────────────────────────────

@admin.register(CompositeProduct)
class CompositeProductAdmin(admin.ModelAdmin):
    list_display    = ['bundle_product', 'component_variant', 'quantity', 'created_at']
    search_fields   = ['bundle_product__name', 'component_variant__name']
    list_per_page   = 25
    list_select_related    = ['bundle_product', 'component_variant']
    raw_id_fields   = ['bundle_product', 'component_variant']
    readonly_fields = ['created_at', 'updated_at']


# ─── Serial Number ────────────────────────────────────────────────────────────

@admin.register(SerialNumber)
class SerialNumberAdmin(admin.ModelAdmin):
    list_display    = ['serial_number', 'variant', 'status_badge', 'sold_at', 'created_at']
    list_filter     = ['status']
    search_fields   = ['serial_number', 'variant__name', 'variant__sku']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['variant']
    raw_id_fields   = ['variant']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Unit',  {'fields': ('variant', 'serial_number', 'status')}),
        ('Dates', {'fields': ('sold_at', 'created_at', 'updated_at')}),
        ('Notes', {'fields': ('notes',)}),
    )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'available': ('#d4edda', '#155724'),
            'reserved':  ('#fff3cd', '#856404'),
            'sold':      ('#cce5ff', '#004085'),
            'returned':  ('#e2e3e5', '#383d41'),
            'damaged':   ('#f8d7da', '#721c24'),
        }
        bg, color = colors.get(obj.status, ('#e2e3e5', '#333'))
        return _badge(obj.get_status_display(), bg, color)
