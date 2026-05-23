from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='points_redeemed',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='reservation',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
    ]
