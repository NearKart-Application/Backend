import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LoyaltyAccount',
            fields=[
                ('id',             models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, db_index=True)),
                ('created_at',     models.DateTimeField(auto_now_add=True)),
                ('updated_at',     models.DateTimeField(auto_now=True)),
                ('balance',        models.PositiveIntegerField(default=0)),
                ('total_earned',   models.PositiveIntegerField(default=0)),
                ('total_redeemed', models.PositiveIntegerField(default=0)),
                ('referral_code',  models.CharField(max_length=10, unique=True)),
                ('user',           models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='loyalty_account',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'loyalty_accounts', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='LoyaltyTransaction',
            fields=[
                ('id',               models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, db_index=True)),
                ('created_at',       models.DateTimeField(auto_now_add=True)),
                ('updated_at',       models.DateTimeField(auto_now=True)),
                ('transaction_type', models.CharField(choices=[('earn', 'Earn'), ('redeem', 'Redeem')], max_length=10)),
                ('source',           models.CharField(choices=[('referral', 'Referral Bonus'), ('redemption', 'Points Redemption'), ('bonus', 'Bonus')], max_length=20)),
                ('points',           models.PositiveIntegerField()),
                ('description',      models.CharField(max_length=200)),
                ('balance_after',    models.PositiveIntegerField(default=0)),
                ('account',          models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='transactions',
                    to='loyalty.loyaltyaccount',
                )),
            ],
            options={'db_table': 'loyalty_transactions', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Referral',
            fields=[
                ('id',            models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, db_index=True)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('updated_at',    models.DateTimeField(auto_now=True)),
                ('referral_code', models.CharField(max_length=10)),
                ('status',        models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed')], default='pending', max_length=20)),
                ('points_awarded',models.PositiveIntegerField(default=0)),
                ('completed_at',  models.DateTimeField(blank=True, null=True)),
                ('referrer',      models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='referrals_given',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('referred',      models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='referral_received',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'loyalty_referrals', 'ordering': ['-created_at']},
        ),
    ]
