"""
NearKart — Loyalty & Referral Models
LoyaltyAccount  : one per user, holds points balance
LoyaltyTransaction : earn / redeem history
Referral        : tracks who referred whom

The user's profile_id (NS code) is the referral code — no separate field needed.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class LoyaltyAccount(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loyalty_account',
    )
    balance        = models.PositiveIntegerField(default=0)
    total_earned   = models.PositiveIntegerField(default=0)
    total_redeemed = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'loyalty_accounts'

    def __str__(self):
        return f'{self.user.phone_number} — {self.balance} pts'

    @classmethod
    def get_or_create_for(cls, user) -> 'LoyaltyAccount':
        obj, _ = cls.objects.get_or_create(user=user)
        return obj


class LoyaltyTransaction(BaseModel):
    EARN   = 'earn'
    REDEEM = 'redeem'
    TYPE_CHOICES = [(EARN, 'Earn'), (REDEEM, 'Redeem')]

    SOURCE_REFERRAL   = 'referral'
    SOURCE_REDEMPTION = 'redemption'
    SOURCE_BONUS      = 'bonus'
    SOURCE_CHOICES = [
        (SOURCE_REFERRAL,   'Referral Bonus'),
        (SOURCE_REDEMPTION, 'Points Redemption'),
        (SOURCE_BONUS,      'Bonus'),
    ]

    account          = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    source           = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    points           = models.PositiveIntegerField()
    description      = models.CharField(max_length=200)
    balance_after    = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'loyalty_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.transaction_type} {self.points} pts — {self.description}'


class Referral(BaseModel):
    STATUS_PENDING   = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES   = [(STATUS_PENDING, 'Pending'), (STATUS_COMPLETED, 'Completed')]

    referrer       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_given')
    referred       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='referral_received')
    referral_code  = models.CharField(max_length=16)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    points_awarded = models.PositiveIntegerField(default=0)
    completed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'loyalty_referrals'

    def __str__(self):
        return f'{self.referrer} → {self.referred} ({self.status})'
