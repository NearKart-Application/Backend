from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('reservations', '0007_reservation_pickup_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='actual_selling_price',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True,
                help_text='Price vendor charged at completion. Used for revenue reports.',
            ),
        ),
    ]
