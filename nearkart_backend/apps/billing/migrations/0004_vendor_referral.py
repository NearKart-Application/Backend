import uuid
import decimal
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_add_vendor_coupon_redemption'),
        ('stores', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReferralConfig',
            fields=[
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('city', models.CharField(blank=True, db_index=True, default='', max_length=150, unique=True)),
                ('vendor_reward', models.DecimalField(decimal_places=2, default=decimal.Decimal('50.00'), max_digits=8)),
                ('customer_reward', models.DecimalField(decimal_places=2, default=decimal.Decimal('20.00'), max_digits=8)),
                ('vendor_reward_min', models.DecimalField(decimal_places=2, default=decimal.Decimal('10.00'), max_digits=8)),
                ('vendor_reward_max', models.DecimalField(decimal_places=2, default=decimal.Decimal('200.00'), max_digits=8)),
                ('customer_reward_min', models.DecimalField(decimal_places=2, default=decimal.Decimal('10.00'), max_digits=8)),
                ('customer_reward_max', models.DecimalField(decimal_places=2, default=decimal.Decimal('200.00'), max_digits=8)),
            ],
            options={'db_table': 'billing_referral_configs'},
        ),
        migrations.CreateModel(
            name='ReferralCode',
            fields=[
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(db_index=True, max_length=16, unique=True)),
                ('store', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='referral',
                    to='stores.store',
                )),
            ],
            options={'db_table': 'billing_referral_codes'},
        ),
        migrations.CreateModel(
            name='UserReferralLink',
            fields=[
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reward_type', models.CharField(choices=[('vendor', 'Vendor Referral'), ('customer', 'Customer Referral')], max_length=20)),
                ('reward_credited', models.BooleanField(default=False)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='referral_link',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('referrer_store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='referred_users',
                    to='stores.store',
                )),
            ],
            options={'db_table': 'billing_user_referral_links'},
        ),
        migrations.CreateModel(
            name='VendorReferral',
            fields=[
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reward_type', models.CharField(max_length=20)),
                ('reward_amount', models.DecimalField(decimal_places=2, max_digits=8)),
                ('referrer_store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='referral_earnings',
                    to='stores.store',
                )),
                ('referred_user', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='referral_reward',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('transaction', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='referral_record',
                    to='billing.transaction',
                )),
            ],
            options={'db_table': 'billing_vendor_referrals', 'ordering': ['-created_at']},
        ),
    ]
