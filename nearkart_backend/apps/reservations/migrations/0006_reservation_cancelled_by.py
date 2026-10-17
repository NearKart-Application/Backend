from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0005_perf_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='cancelled_by',
            field=models.CharField(
                blank=True,
                choices=[('customer', 'Customer'), ('vendor', 'Vendor')],
                default='',
                max_length=20,
            ),
        ),
    ]
