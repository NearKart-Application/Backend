from django.contrib import admin
from .models import LoyaltyAccount, LoyaltyTransaction, Referral


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display  = ['user', 'balance', 'total_earned', 'total_redeemed']
    search_fields = ['user__phone_number', 'user__profile_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display  = ['account', 'transaction_type', 'source', 'points', 'balance_after', 'created_at']
    list_filter   = ['transaction_type', 'source']
    search_fields = ['account__user__phone_number', 'description']
    readonly_fields = ['created_at']


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display  = ['referrer', 'referred', 'referral_code', 'status', 'points_awarded', 'completed_at']
    list_filter   = ['status']
    search_fields = ['referrer__phone_number', 'referred__phone_number', 'referral_code', 'referrer__profile_id']
    readonly_fields = ['created_at', 'completed_at']
