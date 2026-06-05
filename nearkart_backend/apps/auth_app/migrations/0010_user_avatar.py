from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0009_admin_assigned_city_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=models.URLField(blank=True, default=''),
        ),
    ]
