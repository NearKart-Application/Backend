import random
import string
from django.db import migrations, models


def _gen_code(existing: set) -> str:
    chars = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = 'NKP-' + ''.join(random.choices(chars, k=6))
        if code not in existing:
            return code
    return 'NKP-' + ''.join(random.choices(chars, k=9))


def populate_product_codes(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    existing = set()
    products = list(Product.objects.filter(product_code='').order_by('created_at'))
    for product in products:
        code = _gen_code(existing)
        existing.add(code)
        product.product_code = code
        product.save(update_fields=['product_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_stock_models'),
    ]

    operations = [
        # Step 1: add as nullable (safe for existing rows)
        migrations.AddField(
            model_name='product',
            name='product_code',
            field=models.CharField(blank=True, max_length=20, default=''),
            preserve_default=False,
        ),
        # Step 2: backfill existing products with unique codes
        migrations.RunPython(populate_product_codes, migrations.RunPython.noop),
        # Step 3: now safe to add unique + index
        migrations.AlterField(
            model_name='product',
            name='product_code',
            field=models.CharField(blank=True, db_index=True, max_length=20, unique=True),
        ),
    ]
