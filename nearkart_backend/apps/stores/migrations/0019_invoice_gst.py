from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0018_customer_blocked_store'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='gstin',
            field=models.CharField(blank=True, max_length=15),
        ),
        migrations.AddField(
            model_name='invoice',
            name='gst_rate',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
