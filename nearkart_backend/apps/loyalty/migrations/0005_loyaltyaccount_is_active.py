from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loyalty', '0004_add_inventory_notification_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='loyaltyaccount',
            name='is_active',
            field=models.BooleanField(default=True, db_index=True),
        ),
    ]
