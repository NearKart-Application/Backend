from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0015_jewelry_fields_on_variant'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariant',
            name='length_cm',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Product length in centimetres', max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='width_cm',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Product width in centimetres', max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='height_cm',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Product height in centimetres', max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='weight_kg',
            field=models.DecimalField(blank=True, decimal_places=3, help_text='Shipping / physical weight in kilograms', max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='is_assembly_required',
            field=models.BooleanField(default=False, help_text='True if the item ships unassembled and requires self-assembly'),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='is_display_unit',
            field=models.BooleanField(default=False, help_text='True if this variant is a floor/display sample, not fresh stock'),
        ),
    ]
