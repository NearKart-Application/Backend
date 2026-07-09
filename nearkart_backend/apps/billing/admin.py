"""
NearKart — Billing Admin
Shopify-grade admin for Plan, Subscription, Transaction, Coupon,
CouponRedemption, ReferralConfig, ReferralCode, UserReferralLink, VendorReferral.
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Plan, Subscription, Transaction,
    Coupon, CouponRedemption,
    ReferralConfig, ReferralCode, UserReferralLink, VendorReferral,
)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _badge(text, bg, color):
    return format_html(
        '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:{};color:{}">{}</span>',
        bg, color, text
    )


# ─── Plan Admin ───────────────────────────────────────────────────────────────

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display    = [
        'display_name', 'price', 'duration_days', 'store_track',
        'product_limit', 'video_limit', 'supplier_limit', 'po_limit_monthly',
        'is_active_badge',
    ]
    ordering        = ['price']
    list_per_page   = 25
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Plan Details', {'fields': ('name', 'display_name', 'price', 'duration_days',
                                     'store_track', 'is_active', 'description')}),
        ('Limits',       {'fields': ('product_limit', 'video_limit', 'supplier_limit',
                                     'po_limit_monthly', 'movement_log_retention_days')}),
        ('Meta',         {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#f8d7da', '#721c24')


# ─── Subscription Admin ───────────────────────────────────────────────────────

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display    = [
        'store', 'plan', 'started_at', 'expires_at',
        'days_remaining', 'is_active_badge',
    ]
    list_filter     = ['plan', 'is_active']
    search_fields   = ['store__name', 'store__owner__phone_number']
    ordering        = ['-expires_at']
    date_hierarchy  = 'started_at'
    list_per_page   = 25
    show_full_result_count = False
    raw_id_fields   = ['store', 'plan']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related    = ['store', 'plan']

    @admin.display(description='Days Left', ordering='expires_at')
    def days_remaining(self, obj):
        if not obj.is_active:
            return _badge('Expired', '#f8d7da', '#721c24')
        delta = obj.expires_at - timezone.now()
        days = max(0, delta.days)
        if days <= 3:
            return _badge(f'{days}d', '#f8d7da', '#721c24')
        elif days <= 10:
            return _badge(f'{days}d', '#fff3cd', '#856404')
        return _badge(f'{days}d', '#d4edda', '#155724')

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Expired', '#f8d7da', '#721c24')


# ─── Transaction Admin ────────────────────────────────────────────────────────

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display    = [
        'store', 'type_badge', 'amount', 'balance_after',
        'reference_id', 'description', 'created_at',
    ]
    list_filter     = ['type']
    search_fields   = ['store__name', 'reference_id', 'description']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    raw_id_fields   = ['store']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related    = ['store']

    @admin.display(description='Type', ordering='type')
    def type_badge(self, obj):
        colors = {
            'topup':        ('#d4edda', '#155724'),
            'subscription': ('#cce5ff', '#004085'),
            'refund':       ('#fff3cd', '#856404'),
            'referral':     ('#e2e3e5', '#383d41'),
        }
        bg, color = colors.get(obj.type, ('#e2e3e5', '#333'))
        return _badge(obj.get_type_display(), bg, color)


# ─── Coupon Admin ─────────────────────────────────────────────────────────────

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display    = [
        'code', 'discount_percent', 'used_count', 'max_uses',
        'expires_at', 'is_active_badge', 'created_at',
    ]
    list_filter     = ['is_active']
    search_fields   = ['code']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    raw_id_fields   = ['target_store', 'created_by']
    readonly_fields = ['used_count', 'created_at', 'updated_at']

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#f8d7da', '#721c24')


# ─── Coupon Redemption Admin ──────────────────────────────────────────────────

@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display    = [
        'coupon', 'store', 'plan_display',
        'original_price', 'discount_given', 'price_paid', 'redeemed_at',
    ]
    search_fields   = ['coupon__code', 'store__name']
    ordering        = ['-redeemed_at']
    date_hierarchy  = 'redeemed_at'
    list_per_page   = 25
    show_full_result_count = False
    raw_id_fields   = ['coupon', 'store', 'subscription']
    readonly_fields = ['redeemed_at', 'created_at', 'updated_at']
    list_select_related    = ['coupon', 'store']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ─── Referral Config Admin ────────────────────────────────────────────────────

@admin.register(ReferralConfig)
class ReferralConfigAdmin(admin.ModelAdmin):
    list_display    = ['city_display', 'vendor_reward', 'customer_reward',
                       'vendor_reward_min', 'vendor_reward_max']
    list_per_page   = 25
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='City / Scope', ordering='city')
    def city_display(self, obj):
        return obj.city if obj.city else '(Global Default)'


# ─── Referral Code Admin ──────────────────────────────────────────────────────

@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display    = ['code', 'store', 'created_at']
    search_fields   = ['code', 'store__name']
    list_per_page   = 25
    list_select_related    = ['store']
    raw_id_fields   = ['store']
    readonly_fields = ['created_at', 'updated_at']


# ─── User Referral Link Admin ─────────────────────────────────────────────────

@admin.register(UserReferralLink)
class UserReferralLinkAdmin(admin.ModelAdmin):
    list_display    = ['user', 'referrer_store', 'reward_type', 'reward_credited', 'created_at']
    list_filter     = ['reward_type', 'reward_credited']
    search_fields   = ['user__phone_number', 'referrer_store__name']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['user', 'referrer_store']
    raw_id_fields   = ['user', 'referrer_store']
    readonly_fields = ['created_at', 'updated_at']


# ─── Vendor Referral Admin ────────────────────────────────────────────────────

@admin.register(VendorReferral)
class VendorReferralAdmin(admin.ModelAdmin):
    list_display    = ['referrer_store', 'referred_user', 'reward_type', 'reward_amount', 'created_at']
    search_fields   = ['referrer_store__name', 'referred_user__phone_number']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    show_full_result_count = False
    list_select_related    = ['referrer_store', 'referred_user']
    raw_id_fields   = ['referrer_store', 'referred_user', 'transaction']
    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
