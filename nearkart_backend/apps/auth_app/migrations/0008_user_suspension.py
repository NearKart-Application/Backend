from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0007_user_admin_assigned_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_suspended',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='suspension_reason',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
    ]
