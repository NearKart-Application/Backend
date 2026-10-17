from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('loyalty', '0006_walletwithdrawalrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='loyaltytransaction',
            name='expires_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='loyaltytransaction',
            name='is_expired',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
