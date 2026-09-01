from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0013_barcode_variant_image_qa_price_history'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariant',
            name='unit',
            field=models.CharField(
                blank=True,
                default='piece',
                help_text='Unit of measure (piece, kg, gram, litre, dozen, metre, pair)',
                max_length=20,
            ),
        ),
    ]
