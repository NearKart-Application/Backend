from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0006_role_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='admin_assigned_city',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
