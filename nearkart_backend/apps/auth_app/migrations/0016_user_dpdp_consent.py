from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0015_socialaccount'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='consent_given',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='consent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='is_adult_confirmed',
            field=models.BooleanField(default=False),
        ),
    ]
