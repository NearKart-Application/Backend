"""
NearSpot — Customer Credit (Udhar) Models
CustomerCreditAccount: per-store customer record with balance + limit
CreditTransaction:     individual credit sale or payment entry
"""
from django.db import models
from django.utils import timezone
from core.models import BaseModel


class CustomerCreditAccount(BaseModel):
    """One credit account per (store, customer_name+phone) pair."""
    store        = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='credit_accounts')
    name         = models.CharField(max_length=200)
    phone        = models.CharField(max_length=15, blank=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes        = models.TextField(blank=True)
    is_active    = models.BooleanField(default=True)

    class Meta:
        db_table        = 'credit_accounts'
        unique_together = [('store', 'phone')]
        ordering        = ['name']

    def __str__(self):
        return f'{self.name} ({self.store.name})'

    @property
    def balance(self):
        """Positive = amount customer owes; negative = overpaid (credit)."""
        agg = self.transactions.aggregate(
            total=models.Sum('amount', filter=models.Q(transaction_type='credit')),
            paid=models.Sum('amount', filter=models.Q(transaction_type='payment')),
        )
        return (agg['total'] or 0) - (agg['paid'] or 0)

    @property
    def available_credit(self):
        if self.credit_limit <= 0:
            return None  # no limit set
        return max(0, self.credit_limit - self.balance)

    @property
    def days_oldest_unpaid(self):
        oldest = self.transactions.filter(
            transaction_type='credit'
        ).order_by('created_at').first()
        if not oldest:
            return 0
        return (timezone.now().date() - oldest.created_at.date()).days


class CreditTransaction(BaseModel):
    CREDIT  = 'credit'
    PAYMENT = 'payment'
    TYPE_CHOICES = [(CREDIT, 'Credit Sale'), (PAYMENT, 'Payment Received')]

    CASH   = 'cash'
    UPI    = 'upi'
    CARD   = 'card'
    OTHER  = 'other'
    PAY_CHOICES = [(CASH, 'Cash'), (UPI, 'UPI'), (CARD, 'Card'), (OTHER, 'Other')]

    account          = models.ForeignKey(CustomerCreditAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount           = models.DecimalField(max_digits=10, decimal_places=2)
    note             = models.TextField(blank=True)
    payment_method   = models.CharField(max_length=10, choices=PAY_CHOICES, blank=True)
    recorded_by      = models.ForeignKey('auth_app.User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'credit_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.transaction_type} ₹{self.amount} — {self.account.name}'
