import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0013_userloginlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerActivityLog',
            fields=[
                ('id',          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('updated_at',  models.DateTimeField(auto_now=True)),
                ('phone',       models.CharField(blank=True, db_index=True, max_length=20)),
                ('action',      models.CharField(
                    choices=[
                        ('product_view',       'Product Viewed'),
                        ('store_view',         'Store Viewed'),
                        ('search',             'Search'),
                        ('wishlist_add',       'Wishlisted'),
                        ('wishlist_remove',    'Unwishlisted'),
                        ('reservation_create', 'Reservation Made'),
                    ],
                    db_index=True,
                    max_length=25,
                )),
                ('entity_type', models.CharField(blank=True, max_length=20)),
                ('entity_id',   models.CharField(blank=True, db_index=True, max_length=40)),
                ('entity_name', models.CharField(blank=True, max_length=250)),
                ('meta',        models.JSONField(blank=True, default=dict)),
                ('ip_address',  models.GenericIPAddressField(blank=True, null=True)),
                ('city',        models.CharField(blank=True, max_length=150)),
                ('device_type', models.CharField(blank=True, max_length=10)),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='activity_logs',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'customer_activity_logs', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='customeractivitylog',
            index=models.Index(fields=['user', 'created_at'], name='cal_user_idx'),
        ),
        migrations.AddIndex(
            model_name='customeractivitylog',
            index=models.Index(fields=['action', 'created_at'], name='cal_action_idx'),
        ),
    ]
