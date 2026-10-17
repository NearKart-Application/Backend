from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0012_broadcast_channels_posts'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='discount_type',
            field=models.CharField(
                blank=True, max_length=10, null=True,
                choices=[('amount', 'Fixed Amount'), ('percent', 'Percentage')],
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='discount_value',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
