from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0003_reservation_variant_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='cancel_reason',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
