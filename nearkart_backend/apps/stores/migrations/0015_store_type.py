from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0014_remove_discountcode_unique_store_code_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='store_type',
            field=models.CharField(
                choices=[('product', 'Product Store'), ('service', 'Service Store')],
                default='product',
                max_length=10,
            ),
        ),
    ]
