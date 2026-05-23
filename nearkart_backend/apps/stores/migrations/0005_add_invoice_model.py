from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0004_storereview_vendor_reply'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id',             models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',     models.DateTimeField(auto_now_add=True)),
                ('updated_at',     models.DateTimeField(auto_now=True)),
                ('customer_name',  models.CharField(max_length=200)),
                ('customer_phone', models.CharField(blank=True, max_length=20)),
                ('items',          models.JSONField(default=list)),
                ('notes',          models.TextField(blank=True)),
                ('total',          models.DecimalField(decimal_places=2, max_digits=10)),
                ('is_sent',        models.BooleanField(default=False)),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invoices',
                    to='stores.store',
                )),
            ],
            options={
                'db_table': 'store_invoices',
                'ordering': ['-created_at'],
            },
        ),
    ]
