from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0011_user_location_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='location_district',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='user',
            name='location_state',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
    ]
