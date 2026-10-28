import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Switch credit-account uniqueness from conditional to unconditional.

    0001 added a *conditional* UniqueConstraint ``unique_store_phone_credit``
    (implemented by Postgres as a partial unique index, unique only when
    phone != ''), so two accounts with the same store and an EMPTY phone were
    allowed. The model later switched to an unconditional
    ``unique_together(('store', 'phone'))`` with no migration. This migration
    reconciles that: it drops the old partial unique index and adds the
    unconditional unique constraint, closing the empty-phone duplicate gap.

    The credit_accounts table is empty, so the new constraint applies cleanly.
    The id-field AlterFields only reconcile state (db_index on a PK is a no-op).
    """

    dependencies = [
        ('credit', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='customercreditaccount',
            name='unique_store_phone_credit',
        ),
        migrations.AlterUniqueTogether(
            name='customercreditaccount',
            unique_together={('store', 'phone')},
        ),
        migrations.AlterField(
            model_name='customercreditaccount',
            name='id',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='credittransaction',
            name='id',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]
