from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('stores', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpenseCategory',
            fields=[
                ('id',         models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name',       models.CharField(max_length=100)),
                ('is_system',  models.BooleanField(default=False)),
                ('store',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expense_categories', to='stores.store')),
            ],
            options={'db_table': 'expense_categories', 'ordering': ['name']},
        ),
        migrations.AddConstraint(
            model_name='expensecategory',
            constraint=models.UniqueConstraint(fields=['store', 'name'], name='unique_store_expense_category'),
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id',              models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',      models.DateTimeField(auto_now_add=True)),
                ('updated_at',      models.DateTimeField(auto_now=True)),
                ('category_name',   models.CharField(max_length=100, blank=True)),
                ('amount',          models.DecimalField(max_digits=12, decimal_places=2)),
                ('gst_amount',      models.DecimalField(max_digits=10, decimal_places=2, default=0)),
                ('description',     models.TextField(blank=True)),
                ('vendor_name',     models.CharField(max_length=200, blank=True)),
                ('date',            models.DateField()),
                ('receipt_image',   models.ImageField(upload_to='expense_receipts/', null=True, blank=True)),
                ('is_recurring',    models.BooleanField(default=False)),
                ('recurrence_type', models.CharField(max_length=10, blank=True, choices=[('daily','Daily'),('weekly','Weekly'),('monthly','Monthly'),('yearly','Yearly')])),
                ('store',           models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expenses', to='stores.store')),
                ('category',        models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expenses', to='expenses.expensecategory')),
                ('recorded_by',     models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'expenses', 'ordering': ['-date', '-created_at']},
        ),
    ]
