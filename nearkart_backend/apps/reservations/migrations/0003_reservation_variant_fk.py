from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0002_reservation_loyalty_fields'),
        ('products',     '0003_stock_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='variant',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reservations',
                to='products.productvariant',
            ),
        ),
    ]
