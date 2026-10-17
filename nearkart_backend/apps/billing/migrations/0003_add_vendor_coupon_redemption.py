import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_add_coupon_model'),
        ('stores', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add target_store FK to Coupon (null = general coupon)
        migrations.AddField(
            model_name='coupon',
            name='target_store',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='targeted_coupons',
                to='stores.store',
            ),
        ),
        # Add created_by FK to Coupon (which admin created it)
        migrations.AddField(
            model_name='coupon',
            name='created_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_coupons',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Create CouponRedemption audit-trail model
        migrations.CreateModel(
            name='CouponRedemption',
            fields=[
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan_name', models.CharField(max_length=20)),
                ('plan_display', models.CharField(max_length=50)),
                ('original_price', models.DecimalField(max_digits=10, decimal_places=2)),
                ('discount_given', models.DecimalField(max_digits=10, decimal_places=2)),
                ('price_paid', models.DecimalField(max_digits=10, decimal_places=2)),
                ('redeemed_at', models.DateTimeField(auto_now_add=True)),
                ('coupon', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='redemptions',
                    to='billing.coupon',
                )),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='coupon_redemptions',
                    to='stores.store',
                )),
                ('subscription', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='redemptions',
                    to='billing.subscription',
                )),
            ],
            options={
                'db_table': 'billing_coupon_redemptions',
                'ordering': ['-redeemed_at'],
            },
        ),
    ]
