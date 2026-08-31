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
    is_active      = models.BooleanField(default=True, db_index=True)

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
    SOURCE_PENALTY    = 'penalty'
    SOURCE_CHOICES = [
        (SOURCE_REFERRAL,   'Referral Bonus'),
        (SOURCE_REDEMPTION, 'Points Redemption'),
        (SOURCE_BONUS,      'Bonus'),
        (SOURCE_PENALTY,    'Cancellation Penalty'),
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


class WalletWithdrawalRequest(BaseModel):
    METHOD_UPI  = 'upi'
    METHOD_BANK = 'bank'
    METHOD_CHOICES = [
        (METHOD_UPI,  'UPI'),
        (METHOD_BANK, 'Bank Transfer'),
    ]

    STATUS_PENDING   = 'pending'
    STATUS_APPROVED  = 'approved'
    STATUS_REJECTED  = 'rejected'
    STATUS_PROCESSED = 'processed'
    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_APPROVED,  'Approved'),
        (STATUS_REJECTED,  'Rejected'),
        (STATUS_PROCESSED, 'Processed'),
    ]

    user           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet_withdrawal_requests')
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    method         = models.CharField(max_length=10, choices=METHOD_CHOICES)
    upi_id         = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    ifsc_code      = models.CharField(max_length=20, blank=True)
    account_name   = models.CharField(max_length=100, blank=True)
    note           = models.TextField(blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    admin_note     = models.TextField(blank=True)

    class Meta:
        db_table = 'loyalty_wallet_withdrawal_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — ₹{self.amount} via {self.method} ({self.status})'


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
