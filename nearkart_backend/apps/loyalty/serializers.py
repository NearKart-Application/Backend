"""
NearKart — Loyalty Serializers
"""
from rest_framework import serializers
from .models import LoyaltyAccount, LoyaltyTransaction, WalletWithdrawalRequest
from .services import POINTS_PER_RUPEE, MIN_REDEEM, MAX_REDEEM


class LoyaltyBalanceSerializer(serializers.ModelSerializer):
    referral_code          = serializers.SerializerMethodField()
    points_value_rupees    = serializers.SerializerMethodField()
    referrals_count        = serializers.SerializerMethodField()
    tier                   = serializers.SerializerMethodField()
    next_tier_points_needed = serializers.SerializerMethodField()

    class Meta:
        model  = LoyaltyAccount
        fields = [
            'balance', 'total_earned', 'total_redeemed',
            'referral_code', 'points_value_rupees', 'referrals_count',
            'tier', 'next_tier_points_needed',
        ]

    def get_referral_code(self, obj):
        return obj.user.profile_id

    def get_points_value_rupees(self, obj):
        return obj.balance // POINTS_PER_RUPEE

    def get_referrals_count(self, obj):
        return obj.user.referrals_given.filter(status='completed').count()

    def get_tier(self, obj):
        return obj.tier

    def get_next_tier_points_needed(self, obj):
        return obj.next_tier_points_needed


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LoyaltyTransaction
        fields = ['id', 'transaction_type', 'source', 'points', 'description', 'balance_after', 'created_at']


class ApplyReferralSerializer(serializers.Serializer):
    referral_code = serializers.CharField(max_length=16, min_length=13)

    def validate_referral_code(self, value):
        return value.strip().upper()


class RedeemPointsSerializer(serializers.Serializer):
    points      = serializers.IntegerField(min_value=MIN_REDEEM, max_value=MAX_REDEEM)
    description = serializers.CharField(max_length=200, required=False, default='Points redeemed')


class WalletWithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model  = WalletWithdrawalRequest
        fields = [
            'id', 'amount', 'method',
            'upi_id', 'account_number', 'ifsc_code', 'account_name',
            'note', 'status', 'admin_note', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'admin_note', 'created_at']

    def validate(self, data):
        method = data.get('method')
        if method == WalletWithdrawalRequest.METHOD_UPI and not data.get('upi_id', '').strip():
            raise serializers.ValidationError({'upi_id': 'UPI ID is required for UPI method.'})
        if method == WalletWithdrawalRequest.METHOD_BANK:
            for field in ('account_number', 'ifsc_code', 'account_name'):
                if not data.get(field, '').strip():
                    raise serializers.ValidationError({field: f'{field.replace("_", " ").title()} is required for bank transfer.'})
        return data
