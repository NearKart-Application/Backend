from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_add_subcategory_to_product'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StockMovementLog',
            fields=[
                ('id',         models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('old_qty',    models.IntegerField()),
                ('new_qty',    models.IntegerField()),
                ('delta',      models.IntegerField()),
                ('reason',     models.CharField(
                    choices=[('manual','Manual Update'),('reservation','Reservation Deduction'),
                             ('restoration','Reservation Restore'),('restock','Restock')],
                    default='manual', max_length=20,
                )),
                ('note',       models.CharField(blank=True, max_length=200)),
                ('variant',    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                               related_name='stock_logs', to='products.productvariant')),
                ('changed_by', models.ForeignKey(blank=True, null=True,
                               on_delete=django.db.models.deletion.SET_NULL,
                               related_name='stock_changes', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'stock_movement_logs', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='stockmovementlog',
            index=models.Index(fields=['variant', 'created_at'], name='stock_log_variant_idx'),
        ),
        migrations.CreateModel(
            name='StockWatchlist',
            fields=[
                ('id',         models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer',   models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                               related_name='stock_watches', to=settings.AUTH_USER_MODEL)),
                ('product',    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                               related_name='stock_watchers', to='products.product')),
            ],
            options={'db_table': 'stock_watchlist', 'ordering': ['-created_at'],
                     'unique_together': {('customer', 'product')}},
        ),
    ]
