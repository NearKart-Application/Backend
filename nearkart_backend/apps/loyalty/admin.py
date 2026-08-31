"""
NearKart — Loyalty Admin
Shopify-grade admin for LoyaltyAccount, LoyaltyTransaction, Referral.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import LoyaltyAccount, LoyaltyTransaction, Referral, WalletWithdrawalRequest


# ─── Helper ───────────────────────────────────────────────────────────────────

def _badge(text, bg, color):
    return format_html(
        '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:{};color:{}">{}</span>',
        bg, color, text
    )


# ─── Loyalty Account Admin ────────────────────────────────────────────────────

@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display    = ['user_phone', 'balance_display', 'total_earned', 'total_redeemed', 'is_active', 'created_at']
    list_filter     = ['is_active']
    search_fields   = ['user__phone_number', 'user__profile_id']
    ordering        = ['-balance']
    list_per_page   = 25
    list_select_related    = ['user']
    raw_id_fields   = ['user']
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='User', ordering='user__phone_number')
    def user_phone(self, obj):
        return obj.user.phone_number

    @admin.display(description='Balance', ordering='balance')
    def balance_display(self, obj):
        if obj.balance > 100:
            return format_html(
                '<span style="color:#155724;font-weight:600">{} pts</span>', obj.balance
            )
        elif obj.balance > 0:
            return format_html(
                '<span style="color:#856404;font-weight:600">{} pts</span>', obj.balance
            )
        return format_html('<span style="color:#999">0 pts</span>')


# ─── Loyalty Transaction Admin ────────────────────────────────────────────────

@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display    = [
        'account_user', 'type_badge', 'source',
        'points_display', 'balance_after', 'description', 'created_at',
    ]
    list_filter     = ['transaction_type', 'source']
    search_fields   = ['account__user__phone_number', 'description']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['account', 'account__user']
    raw_id_fields   = ['account']
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='User', ordering='account__user__phone_number')
    def account_user(self, obj):
        return obj.account.user.phone_number

    @admin.display(description='Type', ordering='transaction_type')
    def type_badge(self, obj):
        if obj.transaction_type == 'earn':
            return _badge('Earn', '#d4edda', '#155724')
        return _badge('Redeem', '#fff3cd', '#856404')

    @admin.display(description='Points', ordering='points')
    def points_display(self, obj):
        if obj.transaction_type == 'earn':
            return format_html(
                '<span style="color:#155724;font-weight:600">+{}</span>', obj.points
            )
        return format_html(
            '<span style="color:#721c24;font-weight:600">-{}</span>', obj.points
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ─── Referral Admin ───────────────────────────────────────────────────────────

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display    = [
        'referrer_phone', 'referred_phone', 'referral_code',
        'status_badge', 'points_awarded', 'completed_at', 'created_at',
    ]
    list_filter     = ['status']
    search_fields   = ['referrer__phone_number', 'referred__phone_number',
                        'referral_code', 'referrer__profile_id']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['referrer', 'referred']
    raw_id_fields   = ['referrer', 'referred']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']

    @admin.display(description='Referrer', ordering='referrer__phone_number')
    def referrer_phone(self, obj):
        return obj.referrer.phone_number

    @admin.display(description='Referred', ordering='referred__phone_number')
    def referred_phone(self, obj):
        return obj.referred.phone_number if obj.referred else '—'

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        if obj.status == 'completed':
            return _badge('Completed', '#d4edda', '#155724')
        return _badge('Pending', '#fff3cd', '#856404')


# ─── Wallet Withdrawal Request Admin ─────────────────────────────────────────

@admin.register(WalletWithdrawalRequest)
class WalletWithdrawalRequestAdmin(admin.ModelAdmin):
    list_display    = ['user_phone', 'amount', 'method', 'status_badge', 'created_at']
    list_filter     = ['status', 'method']
    search_fields   = ['user__phone_number', 'upi_id', 'account_number']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related = ['user']
    raw_id_fields   = ['user']
    readonly_fields = ['created_at', 'updated_at', 'user', 'amount', 'method',
                       'upi_id', 'account_number', 'ifsc_code', 'account_name', 'note']
    fields          = ['user', 'amount', 'method', 'upi_id', 'account_number',
                       'ifsc_code', 'account_name', 'note', 'status', 'admin_note',
                       'created_at', 'updated_at']

    @admin.display(description='User', ordering='user__phone_number')
    def user_phone(self, obj):
        return obj.user.phone_number

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colours = {
            'pending':   ('#fff3cd', '#856404'),
            'approved':  ('#d4edda', '#155724'),
            'rejected':  ('#f8d7da', '#721c24'),
            'processed': ('#cce5ff', '#004085'),
        }
        bg, fg = colours.get(obj.status, ('#eee', '#333'))
        return _badge(obj.status.capitalize(), bg, fg)

    def has_add_permission(self, request):
        return False
