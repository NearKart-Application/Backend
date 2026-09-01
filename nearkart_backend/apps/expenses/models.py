from django.db import models
from django.conf import settings
from core.models import BaseModel


PREDEFINED_CATEGORIES = [
    'Rent', 'Electricity', 'Water', 'Internet', 'Salary', 'Staff Wages',
    'Packaging', 'Transport', 'Marketing', 'Equipment', 'Repairs', 'Miscellaneous',
]

RECURRENCE_CHOICES = [
    ('daily',   'Daily'),
    ('weekly',  'Weekly'),
    ('monthly', 'Monthly'),
    ('yearly',  'Yearly'),
]


class ExpenseCategory(BaseModel):
    store       = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='expense_categories')
    name        = models.CharField(max_length=100)
    is_system   = models.BooleanField(default=False)

    class Meta:
        db_table = 'expense_categories'
        ordering = ['name']
        unique_together = [('store', 'name')]

    def __str__(self):
        return self.name


class Expense(BaseModel):
    store           = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='expenses')
    category        = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    category_name   = models.CharField(max_length=100, blank=True)
    amount          = models.DecimalField(max_digits=12, decimal_places=2)
    gst_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description     = models.TextField(blank=True)
    vendor_name     = models.CharField(max_length=200, blank=True)
    date            = models.DateField()
    receipt_image   = models.ImageField(upload_to='expense_receipts/', null=True, blank=True)
    is_recurring    = models.BooleanField(default=False)
    recurrence_type = models.CharField(max_length=10, choices=RECURRENCE_CHOICES, blank=True)
    recorded_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'expenses'
        ordering = ['-date', '-created_at']

    @property
    def total_amount(self):
        return self.amount + self.gst_amount

    def save(self, *args, **kwargs):
        if self.category and not self.category_name:
            self.category_name = self.category.name
        super().save(*args, **kwargs)
