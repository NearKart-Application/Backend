from django.db import migrations, models


class Migration(migrations.Migration):
    """Reconcile the Transaction.type -> Transaction.transaction_type rename.

    The model field was renamed to ``transaction_type`` but kept ``db_column='type'``,
    so the actual DB column is (and must stay) ``type``. This is a STATE-ONLY
    migration (SeparateDatabaseAndState with empty ``database_operations``): it brings
    the recorded migration state in line with the model WITHOUT touching the table.
    A plain RenameField would wrongly rename the column to ``transaction_type`` and
    re-break wallet transactions.
    """

    dependencies = [
        ('billing', '0006_add_inventory_plan_limits'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(
                    model_name='transaction',
                    old_name='type',
                    new_name='transaction_type',
                ),
                migrations.AlterField(
                    model_name='transaction',
                    name='transaction_type',
                    field=models.CharField(
                        choices=[
                            ('topup', 'Wallet Top-up'),
                            ('subscription', 'Subscription Purchase'),
                            ('refund', 'Refund'),
                            ('referral', 'Referral Reward'),
                        ],
                        db_column='type',
                        max_length=20,
                    ),
                ),
            ],
        ),
    ]
