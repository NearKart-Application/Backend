"""
Area 13 #55 — Remove duplicate StockMovementLog from inventory app.
Canonical model is apps.products.StockMovementLog (table: stock_movement_logs).
The inv_stock_movement_logs table is kept for historical data but the model
is no longer managed by this app.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_add_return_from_customer_reason'),
    ]

    operations = [
        migrations.DeleteModel(
            name='StockMovementLog',
        ),
    ]
