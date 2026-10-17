"""
NearKart — Reservations Admin
Shopify-grade admin for Reservation.
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Reservation


# ─── Helper ───────────────────────────────────────────────────────────────────

def _badge(text, bg, color):
    return format_html(
        '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:{};color:{}">{}</span>',
        bg, color, text
    )


# ─── Reservation Admin ────────────────────────────────────────────────────────

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display    = [
        'short_id', 'customer_phone', 'store', 'product',
        'quantity', 'status_badge', 'expires_at', 'is_expired_badge', 'created_at',
    ]
    list_filter     = ['status']
    search_fields   = ['customer__phone_number', 'store__name', 'product__name']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    show_full_result_count = False
    list_select_related    = ['customer', 'store', 'product']
    raw_id_fields   = ['customer', 'store', 'product', 'variant']
    readonly_fields = ['id', 'expires_at', 'created_at', 'updated_at']

    fieldsets = (
        ('Reservation', {'fields': ('customer', 'store', 'product', 'variant',
                                    'quantity', 'note', 'vendor_note')}),
        ('Status',      {'fields': ('status', 'cancel_reason', 'cancelled_by', 'expires_at')}),
        ('Loyalty',     {'fields': ('points_redeemed', 'discount_amount')}),
        ('Meta',        {'fields': ('id', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='ID')
    def short_id(self, obj):
        return str(obj.id)[:8].upper()

    @admin.display(description='Customer', ordering='customer__phone_number')
    def customer_phone(self, obj):
        return obj.customer.phone_number

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'pending':   ('#fff3cd', '#856404'),
            'confirmed': ('#d4edda', '#155724'),
            'cancelled': ('#f8d7da', '#721c24'),
            'expired':   ('#e2e3e5', '#383d41'),
            'completed': ('#cce5ff', '#004085'),
        }
        bg, color = colors.get(obj.status, ('#e2e3e5', '#333'))
        return _badge(obj.get_status_display(), bg, color)

    @admin.display(description='Past Due')
    def is_expired_badge(self, obj):
        if obj.status in ('expired', 'cancelled', 'completed'):
            return format_html('<span style="color:#999">—</span>')
        if timezone.now() > obj.expires_at:
            return _badge('Yes', '#f8d7da', '#721c24')
        return _badge('No', '#d4edda', '#155724')
