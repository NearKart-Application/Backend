from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('reservations', '0008_area14_reservation_actual_selling_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='payment_method',
            field=models.CharField(
                max_length=20, blank=True, default='',
                choices=[
                    ('cash',   'Cash'),
                    ('upi',    'UPI'),
                    ('card',   'Card'),
                    ('credit', 'Credit (Udhar)'),
                    ('other',  'Other'),
                ],
                help_text='How the customer paid at pickup.',
            ),
        ),
    ]
