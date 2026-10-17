from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_vendor_referral'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='store_track',
            field=models.CharField(
                choices=[
                    ('both',    'All Vendors'),
                    ('product', 'Product Vendors Only'),
                    ('service', 'Service Vendors Only'),
                ],
                default='both',
                max_length=10,
            ),
        ),
    ]
