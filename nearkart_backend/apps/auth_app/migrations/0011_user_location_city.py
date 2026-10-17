from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0010_user_avatar'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='location_city',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
    ]
