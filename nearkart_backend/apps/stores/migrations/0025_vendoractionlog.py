import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0024_storeoffer_discount_type_value'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VendorActionLog',
            fields=[
                ('id',          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('updated_at',  models.DateTimeField(auto_now=True)),
                ('action',      models.CharField(
                    choices=[
                        ('product_create',     'Product Created'),
                        ('product_update',     'Product Updated'),
                        ('product_delete',     'Product Deleted'),
                        ('image_upload',       'Image Uploaded'),
                        ('image_delete',       'Image Deleted'),
                        ('stock_update',       'Stock Updated'),
                        ('stock_bulk_update',  'Bulk Stock Update'),
                        ('offer_create',       'Offer Created'),
                        ('offer_delete',       'Offer Deleted'),
                        ('store_update',       'Store Updated'),
                        ('store_hours_update', 'Hours Updated'),
                    ],
                    db_index=True,
                    max_length=30,
                )),
                ('entity_type', models.CharField(blank=True, max_length=30)),
                ('entity_id',   models.CharField(blank=True, db_index=True, max_length=40)),
                ('entity_name', models.CharField(blank=True, max_length=250)),
                ('meta',        models.JSONField(blank=True, default=dict)),
                ('ip_address',  models.GenericIPAddressField(blank=True, null=True)),
                ('user',  models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='vendor_action_logs',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('store', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='action_logs',
                    to='stores.store',
                )),
            ],
            options={'db_table': 'vendor_action_logs', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='vendoractionlog',
            index=models.Index(fields=['store', 'created_at'], name='val_store_idx'),
        ),
        migrations.AddIndex(
            model_name='vendoractionlog',
            index=models.Index(fields=['user', 'created_at'], name='val_user_idx'),
        ),
    ]
