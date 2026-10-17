from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0021_add_vendor_type_home_based_service_catalogue'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='area',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='store',
            name='city',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='store',
            name='district',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='store',
            name='state',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='store',
            name='country',
            field=models.CharField(blank=True, default='India', max_length=100),
        ),
    ]
