from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0006_reservation_cancelled_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='pickup_time',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
