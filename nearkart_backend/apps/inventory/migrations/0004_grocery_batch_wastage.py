from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_area13_remove_duplicate_stockmovementlog'),
        ('products', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GroceryBatch',
            fields=[
                ('id',              models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',      models.DateTimeField(auto_now_add=True)),
                ('updated_at',      models.DateTimeField(auto_now=True)),
                ('batch_number',    models.CharField(max_length=100, blank=True)),
                ('quantity',        models.DecimalField(max_digits=12, decimal_places=3)),
                ('remaining_qty',   models.DecimalField(max_digits=12, decimal_places=3)),
                ('unit',            models.CharField(max_length=10, choices=[('kg','Kilogram (kg)'),('g','Gram (g)'),('l','Litre (L)'),('ml','Millilitre (mL)'),('piece','Piece / Unit')], default='piece')),
                ('unit_price',      models.DecimalField(max_digits=10, decimal_places=2)),
                ('manufacture_date', models.DateField(null=True, blank=True)),
                ('expiry_date',     models.DateField(null=True, blank=True)),
                ('is_perishable',   models.BooleanField(default=False)),
                ('temperature_zone', models.CharField(max_length=15, choices=[('ambient','Ambient (Room Temp)'),('refrigerated','Refrigerated (2–8°C)'),('frozen','Frozen (< −18°C)')], default='ambient', blank=True)),
                ('notes',           models.TextField(blank=True)),
                ('variant',         models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grocery_batches', to='products.productvariant')),
            ],
            options={'db_table': 'inv_grocery_batches', 'ordering': ['expiry_date', '-created_at']},
        ),
        migrations.AddIndex(
            model_name='grocerybatch',
            index=models.Index(fields=['variant', 'expiry_date'], name='inv_gb_variant_expiry_idx'),
        ),
        migrations.CreateModel(
            name='WastageRecord',
            fields=[
                ('id',          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('updated_at',  models.DateTimeField(auto_now=True)),
                ('quantity',    models.DecimalField(max_digits=12, decimal_places=3)),
                ('reason',      models.CharField(max_length=20, choices=[('expired','Expired'),('damaged','Damaged'),('spillage','Spillage'),('other','Other')], default='expired')),
                ('notes',       models.TextField(blank=True)),
                ('batch',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wastage_records', to='inventory.grocerybatch')),
                ('recorded_by', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'inv_wastage_records', 'ordering': ['-created_at']},
        ),
    ]
