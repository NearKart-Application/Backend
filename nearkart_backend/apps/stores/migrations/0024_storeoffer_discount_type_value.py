from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0023_storehours_timestamps'),
    ]

    operations = [
        migrations.AddField(
            model_name='storeoffer',
            name='discount_type',
            field=models.CharField(
                blank=True, null=True, max_length=10,
                choices=[('percent', 'Percentage'), ('flat', 'Flat Amount')],
            ),
        ),
        migrations.AddField(
            model_name='storeoffer',
            name='discount_value',
            field=models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2),
        ),
    ]
