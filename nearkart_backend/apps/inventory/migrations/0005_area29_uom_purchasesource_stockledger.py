"""
Area 29 — Phase 1 backend architecture models:
  #56  UnitOfMeasure
  #58  PurchaseSource (informal markets)
  #59  StockLedger consolidation
"""
import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_grocery_batch_wastage'),
        ('products',  '0001_initial'),
        ('stores',    '0001_initial'),
    ]

    operations = [

        # ── #56: UnitOfMeasure ────────────────────────────────────────────────
        migrations.CreateModel(
            name='UnitOfMeasure',
            fields=[
                ('id',                models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',        models.DateTimeField(auto_now_add=True)),
                ('updated_at',        models.DateTimeField(auto_now=True)),
                ('name',              models.CharField(max_length=50, unique=True)),
                ('symbol',            models.CharField(max_length=10, unique=True)),
                ('category',          models.CharField(
                    max_length=10,
                    choices=[('weight', 'Weight'), ('volume', 'Volume'), ('count', 'Count / Unit'), ('length', 'Length')],
                    default='count',
                )),
                ('conversion_factor', models.DecimalField(
                    max_digits=15, decimal_places=6, default=1.0,
                    help_text='Multiply by this factor to convert to the base unit of the same category',
                )),
                ('is_base_unit',      models.BooleanField(default=False, help_text='True for kg, litre, piece, metre')),
                ('notes',             models.CharField(max_length=200, blank=True)),
            ],
            options={'db_table': 'inv_units_of_measure', 'ordering': ['category', 'name']},
        ),
        migrations.AddIndex(
            model_name='unitofmeasure',
            index=models.Index(fields=['category', 'is_base_unit'], name='inv_uom_cat_base_idx'),
        ),

        # ── #58: PurchaseSource ───────────────────────────────────────────────
        migrations.CreateModel(
            name='PurchaseSource',
            fields=[
                ('id',           models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('updated_at',   models.DateTimeField(auto_now=True)),
                ('name',         models.CharField(max_length=200)),
                ('market_type',  models.CharField(
                    max_length=20,
                    choices=[
                        ('informal',  'Informal / Street Market'),
                        ('wholesale', 'Wholesale Market'),
                        ('mandi',     'Mandi / Agricultural Market'),
                        ('direct',    'Direct from Farmer / Producer'),
                        ('online',    'Online Supplier'),
                        ('formal',    'Formal Distributor'),
                    ],
                    default='informal',
                )),
                ('contact_name', models.CharField(max_length=200, blank=True)),
                ('phone',        models.CharField(max_length=15, blank=True)),
                ('address',      models.TextField(blank=True)),
                ('notes',        models.TextField(blank=True)),
                ('is_active',    models.BooleanField(default=True)),
                ('store',        models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='purchase_sources',
                    to='stores.store',
                )),
            ],
            options={'db_table': 'inv_purchase_sources', 'ordering': ['name']},
        ),
        migrations.AddIndex(
            model_name='purchasesource',
            index=models.Index(fields=['store', 'market_type', 'is_active'], name='inv_ps_store_type_idx'),
        ),

        # ── #59: StockLedger ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='StockLedger',
            fields=[
                ('id',          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('updated_at',  models.DateTimeField(auto_now=True)),
                ('period_date', models.DateField()),
                ('opening_qty', models.DecimalField(max_digits=12, decimal_places=3, default=0)),
                ('in_qty',      models.DecimalField(
                    max_digits=12, decimal_places=3, default=0,
                    help_text='Total stock received (purchases + returns) this day',
                )),
                ('out_qty',     models.DecimalField(
                    max_digits=12, decimal_places=3, default=0,
                    help_text='Total stock dispatched (sales + wastage) this day',
                )),
                ('closing_qty', models.DecimalField(max_digits=12, decimal_places=3, default=0)),
                ('notes',       models.TextField(blank=True)),
                ('store',       models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='stock_ledger_entries',
                    to='stores.store',
                )),
                ('variant',     models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ledger_entries',
                    to='products.productvariant',
                )),
            ],
            options={'db_table': 'inv_stock_ledger', 'ordering': ['-period_date']},
        ),
        migrations.AlterUniqueTogether(
            name='stockledger',
            unique_together={('store', 'variant', 'period_date')},
        ),
        migrations.AddIndex(
            model_name='stockledger',
            index=models.Index(fields=['store', 'period_date'], name='inv_sl_store_date_idx'),
        ),
        migrations.AddIndex(
            model_name='stockledger',
            index=models.Index(fields=['variant', 'period_date'], name='inv_sl_variant_date_idx'),
        ),
    ]
