"""
NearKart — Notifications Admin
Shopify-grade admin for Notification.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Notification


# ─── Type → badge colour map ─────────────────────────────────────────────────

_TYPE_COLORS = {
    # Chat
    'new_message':              ('#cce5ff', '#004085'),
    # Reservations
    'reservation_created':      ('#e8d5f0', '#4a235a'),
    'reservation_confirmed':    ('#d4edda', '#155724'),
    'reservation_cancelled':    ('#f8d7da', '#721c24'),
    'reservation_expired':      ('#f8d7da', '#721c24'),
    'reservation_expiring_soon':('#fff3cd', '#856404'),
    # Store
    'new_follower':             ('#cce5ff', '#004085'),
    'new_review':               ('#e2e3e5', '#383d41'),
    'store_opened':             ('#d4edda', '#155724'),
    'new_offer':                ('#fff3cd', '#856404'),
    # Videos
    'video_liked':              ('#e2e3e5', '#383d41'),
    'video_ready':              ('#d4edda', '#155724'),
    'video_expiring_soon':      ('#fff3cd', '#856404'),
    # Billing
    'wallet_topup':             ('#d4edda', '#155724'),
    'subscription_expiring':    ('#fff3cd', '#856404'),
    'subscription_expired':     ('#f8d7da', '#721c24'),
    # Inventory / stock
    'low_stock':                ('#fff3cd', '#856404'),
    'out_of_stock_alert':       ('#f8d7da', '#721c24'),
    'back_in_stock':            ('#d4edda', '#155724'),
    'reorder_point':            ('#fff3cd', '#856404'),
    # Loyalty
    'loyalty':                  ('#cce5ff', '#004085'),
    'referral_reward':          ('#d4edda', '#155724'),
}


# ─── Bulk actions ─────────────────────────────────────────────────────────────

@admin.action(description='Mark selected notifications as read')
def mark_all_read(modeladmin, request, queryset):
    updated = queryset.filter(is_read=False).update(is_read=True)
    modeladmin.message_user(request, f'{updated} notification(s) marked as read.')


# ─── Notification Admin ───────────────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display    = [
        'recipient_phone', 'type_badge', 'title', 'read_badge', 'created_at',
    ]
    list_filter     = ['notification_type', 'is_read']
    search_fields   = ['recipient__phone_number', 'title', 'body']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['recipient']
    raw_id_fields   = ['recipient']
    readonly_fields = ['id', 'created_at', 'updated_at', 'data']
    actions         = [mark_all_read]

    @admin.display(description='Recipient', ordering='recipient__phone_number')
    def recipient_phone(self, obj):
        return obj.recipient.phone_number

    @admin.display(description='Type', ordering='notification_type')
    def type_badge(self, obj):
        bg, color = _TYPE_COLORS.get(obj.notification_type, ('#e2e3e5', '#333'))
        return format_html(
            '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
            'font-weight:600;background:{};color:{}">{}</span>',
            bg, color, obj.get_notification_type_display()
        )

    @admin.display(description='Read', ordering='is_read')
    def read_badge(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
                'font-weight:600;background:#d4edda;color:#155724">Read</span>'
            )
        return format_html(
            '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
            'font-weight:600;background:#fff3cd;color:#856404">Unread</span>'
        )
