import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loyalty', '0005_loyaltyaccount_is_active'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WalletWithdrawalRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('method', models.CharField(choices=[('upi', 'UPI'), ('bank', 'Bank Transfer')], max_length=10)),
                ('upi_id', models.CharField(blank=True, max_length=100)),
                ('account_number', models.CharField(blank=True, max_length=30)),
                ('ifsc_code', models.CharField(blank=True, max_length=20)),
                ('account_name', models.CharField(blank=True, max_length=100)),
                ('note', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('approved', 'Approved'),
                        ('rejected', 'Rejected'),
                        ('processed', 'Processed'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('admin_note', models.TextField(blank=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='wallet_withdrawal_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'loyalty_wallet_withdrawal_requests',
                'ordering': ['-created_at'],
            },
        ),
    ]
