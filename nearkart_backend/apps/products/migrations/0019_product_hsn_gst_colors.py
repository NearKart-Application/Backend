from django.db import migrations, models


class Migration(migrations.Migration):
    """Add product-level HSN code, GST rate, and a real colours list.

    Hand-written (not via makemigrations) to avoid an unrelated, pre-existing
    autodetector prompt about billing.Transaction. All three columns use constant
    defaults / NULL, so this is a metadata-only change on PostgreSQL 11+.
    """

    dependencies = [
        ('products', '0018_relative_product_image_urls'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='hsn_code',
            field=models.CharField(blank=True, default='', help_text='HSN/SAC code for GST tax classification', max_length=8),
        ),
        migrations.AddField(
            model_name='product',
            name='gst_rate',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='GST rate % (e.g. 0, 5, 12, 18, 28)', max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='colors',
            field=models.JSONField(blank=True, default=list, help_text='Colour options shown to customers, e.g. ["Red","Blue"]'),
        ),
    ]
