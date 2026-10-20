from django.db import migrations, models


class Migration(migrations.Migration):
    """New products default to Active (visible) instead of Draft.

    Default-only change (no DB schema change); existing rows are untouched.
    """

    dependencies = [
        ('products', '0016_home_decor_fields_on_variant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='status',
            field=models.CharField(
                max_length=20,
                default='active',
                choices=[
                    ('draft', 'Draft'),
                    ('active', 'Active'),
                    ('inactive', 'Inactive'),
                    ('out_of_stock', 'Out of Stock'),
                    ('blacklisted', 'Blacklisted'),
                ],
            ),
        ),
    ]
