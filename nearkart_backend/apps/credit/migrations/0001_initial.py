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
            name='CustomerCreditAccount',
            fields=[
                ('id',           models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('updated_at',   models.DateTimeField(auto_now=True)),
                ('name',         models.CharField(max_length=200)),
                ('phone',        models.CharField(max_length=15, blank=True)),
                ('credit_limit', models.DecimalField(max_digits=10, decimal_places=2, default=0)),
                ('notes',        models.TextField(blank=True)),
                ('is_active',    models.BooleanField(default=True)),
                ('store',        models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credit_accounts', to='stores.store')),
            ],
            options={'db_table': 'credit_accounts', 'ordering': ['name']},
        ),
        migrations.AddConstraint(
            model_name='customercreditaccount',
            constraint=models.UniqueConstraint(fields=['store', 'phone'], name='unique_store_phone_credit', condition=models.Q(phone__gt='')),
        ),
        migrations.CreateModel(
            name='CreditTransaction',
            fields=[
                ('id',               models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',       models.DateTimeField(auto_now_add=True)),
                ('updated_at',       models.DateTimeField(auto_now=True)),
                ('transaction_type', models.CharField(max_length=10, choices=[('credit', 'Credit Sale'), ('payment', 'Payment Received')])),
                ('amount',           models.DecimalField(max_digits=10, decimal_places=2)),
                ('note',             models.TextField(blank=True)),
                ('payment_method',   models.CharField(max_length=10, blank=True, choices=[('cash','Cash'),('upi','UPI'),('card','Card'),('other','Other')])),
                ('account',          models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='credit.customercreditaccount')),
                ('recorded_by',      models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'credit_transactions', 'ordering': ['-created_at']},
        ),
    ]
