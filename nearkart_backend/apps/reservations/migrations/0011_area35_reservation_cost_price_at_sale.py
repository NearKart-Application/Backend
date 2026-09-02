from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('reservations', '0010_area34_reservation_served_by'),
    ]
    operations = [
        migrations.AddField(
            model_name='reservation',
            name='cost_price_at_sale',
            field=models.DecimalField(
                blank=True, null=True,
                max_digits=10, decimal_places=2,
                help_text='Snapshot of variant.cost_price at reservation creation. Enables gross margin = (actual_selling_price - cost_price_at_sale) × quantity.',
            ),
        ),
    ]
