from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_product_festival_tag'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='previous_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
