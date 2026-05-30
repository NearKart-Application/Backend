"""
NearKart — Loyalty & Referral Models
LoyaltyAccount  : one per user, holds points balance + unique referral code
LoyaltyTransaction : earn / redeem history
Referral        : tracks who referred whom
"""
import random
import string

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


def _make_referral_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return 'NS' + ''.join(random.choices(chars, k=6))


class LoyaltyAccount(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loyalty_account',
    )
    balance        = models.PositiveIntegerField(default=0)
    total_earned   = models.PositiveIntegerField(default=0)
    total_redeemed = models.PositiveIntegerField(default=0)
    referral_code  = models.CharField(max_length=10, unique=True)

    class Meta:
        db_table = 'loyalty_accounts'

    def __str__(self):
        return f'{self.user.phone_number} — {self.balance} pts ({self.referral_code})'

    @classmethod
    def get_or_create_for(cls, user) -> 'LoyaltyAccount':
        try:
            return cls.objects.get(user=user)
        except cls.DoesNotExist:
            code = _make_referral_code()
            while cls.objects.filter(referral_code=code).exists():
                code = _make_referral_code()
            return cls.objects.create(user=user, referral_code=code)


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
    referral_code  = models.CharField(max_length=10)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    points_awarded = models.PositiveIntegerField(default=0)
    completed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'loyalty_referrals'

    def __str__(self):
        return f'{self.referrer} → {self.referred} ({self.status})'
