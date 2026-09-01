from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0014_productvariant_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariant',
            name='weight_grams',
            field=models.DecimalField(blank=True, decimal_places=3, help_text='Net weight in grams (gold/silver/platinum)', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='price_per_gram',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Live metal rate in ₹/gram used to compute base price', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='purity',
            field=models.CharField(blank=True, help_text='e.g. 22K, 18K, 14K, 925 (sterling silver), 950 (platinum)', max_length=20),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='making_charges',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Labour / craftsmanship fee in ₹, separate from metal value', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='hallmark_number',
            field=models.CharField(blank=True, help_text='BIS Hallmark certification number (HUID)', max_length=50),
        ),
    ]
