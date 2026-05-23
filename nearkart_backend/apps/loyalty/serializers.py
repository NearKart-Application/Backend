"""
NearKart — Loyalty Serializers
"""
from rest_framework import serializers
from .models import LoyaltyAccount, LoyaltyTransaction
from .services import POINTS_PER_RUPEE, MIN_REDEEM, MAX_REDEEM


class LoyaltyBalanceSerializer(serializers.ModelSerializer):
    points_value_rupees = serializers.SerializerMethodField()
    referrals_count     = serializers.SerializerMethodField()

    class Meta:
        model  = LoyaltyAccount
        fields = [
            'balance', 'total_earned', 'total_redeemed',
            'referral_code', 'points_value_rupees', 'referrals_count',
        ]

    def get_points_value_rupees(self, obj):
        return obj.balance // POINTS_PER_RUPEE

    def get_referrals_count(self, obj):
        return obj.user.referrals_given.filter(status='completed').count()


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LoyaltyTransaction
        fields = ['id', 'transaction_type', 'source', 'points', 'description', 'balance_after', 'created_at']


class ApplyReferralSerializer(serializers.Serializer):
    referral_code = serializers.CharField(max_length=10, min_length=4)

    def validate_referral_code(self, value):
        return value.strip().upper()


class RedeemPointsSerializer(serializers.Serializer):
    points      = serializers.IntegerField(min_value=MIN_REDEEM, max_value=MAX_REDEEM)
    description = serializers.CharField(max_length=200, required=False, default='Points redeemed')
