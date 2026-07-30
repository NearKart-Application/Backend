from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0010_stockwatchlist_notified_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productimage',
            name='s3_key',
            field=models.CharField(max_length=500, blank=True),
        ),
    ]
