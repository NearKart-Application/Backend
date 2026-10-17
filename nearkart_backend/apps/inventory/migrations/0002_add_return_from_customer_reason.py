from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Adds RETURN_FROM_CUSTOMER and AUDIT_ADJUSTMENT to StockMovementReason.
    CharField choices are Python-level only — no SQL change, purely state.
    """

    dependencies = [
        ('inventory', '0001_create_inventory_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stockmovementlog',
            name='reason',
            field=__import__('django.db.models', fromlist=['CharField']).CharField(
                choices=[
                    ('manual',               'Manual Update'),
                    ('reservation',          'Reservation Placed'),
                    ('restoration',          'Reservation Cancelled/Expired'),
                    ('invoice',              'Invoice Sale'),
                    ('purchase',             'Purchase Order Received'),
                    ('return',               'Customer Return'),
                    ('return_from_customer', 'Customer Return (Invoice)'),
                    ('damage',               'Damaged / Written Off'),
                    ('correction',           'Stock Audit Correction'),
                    ('audit_adjustment',     'Stock Audit Adjustment'),
                ],
                max_length=20,
            ),
        ),
    ]
