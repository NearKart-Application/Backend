import uuid
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('stores', '0027_area14_store_review_flag'),
        ('reservations', '0008_area14_reservation_actual_selling_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='Consumable',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('unit', models.CharField(choices=[('ml', 'Millilitre'), ('litre', 'Litre'), ('gram', 'Gram'), ('kg', 'Kilogram'), ('piece', 'Piece'), ('bottle', 'Bottle'), ('sachet', 'Sachet'), ('pair', 'Pair')], default='piece', max_length=20)),
                ('current_stock', models.DecimalField(decimal_places=3, default=0, max_digits=10)),
                ('reorder_level', models.DecimalField(decimal_places=3, default=0, max_digits=10)),
                ('cost_per_unit', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('notes', models.TextField(blank=True)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consumables', to='stores.store')),
            ],
            options={'db_table': 'svc_consumables', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('serial_number', models.CharField(blank=True, max_length=100)),
                ('purchase_date', models.DateField(blank=True, null=True)),
                ('last_maintenance_date', models.DateField(blank=True, null=True)),
                ('next_maintenance_date', models.DateField(blank=True, null=True)),
                ('maintenance_interval_days', models.PositiveIntegerField(blank=True, help_text='Days between scheduled maintenance', null=True)),
                ('condition', models.CharField(choices=[('good', 'Good'), ('fair', 'Fair'), ('needs_repair', 'Needs Repair'), ('out_of_service', 'Out of Service')], default='good', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment', to='stores.store')),
            ],
            options={'db_table': 'svc_equipment', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(help_text='e.g. Chair 1, Bay A, Treatment Room 2', max_length=100)),
                ('resource_type', models.CharField(choices=[('chair', 'Chair'), ('bay', 'Bay'), ('room', 'Room'), ('table', 'Table'), ('other', 'Other')], default='chair', max_length=20)),
                ('capacity', models.PositiveIntegerField(default=1)),
                ('is_active', models.BooleanField(default=True)),
                ('notes', models.CharField(blank=True, max_length=200)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resources', to='stores.store')),
            ],
            options={'db_table': 'svc_resources', 'ordering': ['resource_type', 'name']},
        ),
        migrations.CreateModel(
            name='ServiceConsumable',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantity_per_session', models.DecimalField(decimal_places=3, max_digits=10)),
                ('notes', models.CharField(blank=True, max_length=200)),
                ('consumable', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_links', to='services_inventory.consumable')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consumables', to='stores.servicecatalogue')),
            ],
            options={'db_table': 'svc_service_consumables', 'unique_together': {('service', 'consumable')}},
        ),
        migrations.CreateModel(
            name='MaintenanceRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('date', models.DateField()),
                ('performed_by', models.CharField(blank=True, max_length=200)),
                ('cost', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('description', models.TextField()),
                ('next_due', models.DateField(blank=True, null=True)),
                ('equipment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='maintenance_records', to='services_inventory.equipment')),
            ],
            options={'db_table': 'svc_maintenance_records', 'ordering': ['-date']},
        ),
        migrations.CreateModel(
            name='ResourceAllocation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('staff_name', models.CharField(blank=True, max_length=100)),
                ('date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('notes', models.CharField(blank=True, max_length=200)),
                ('reservation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resource_allocations', to='reservations.reservation')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocations', to='services_inventory.resource')),
            ],
            options={'db_table': 'svc_resource_allocations', 'ordering': ['date', 'start_time']},
        ),
        migrations.AddIndex(
            model_name='consumable',
            index=models.Index(fields=['store', 'name'], name='svc_cons_store_name_idx'),
        ),
        migrations.AddIndex(
            model_name='equipment',
            index=models.Index(fields=['store', 'condition'], name='svc_equip_store_cond_idx'),
        ),
        migrations.AddIndex(
            model_name='resourceallocation',
            index=models.Index(fields=['resource', 'date'], name='svc_alloc_res_date_idx'),
        ),
    ]
