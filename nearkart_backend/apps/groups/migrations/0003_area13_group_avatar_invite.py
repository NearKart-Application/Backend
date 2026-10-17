import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('groups', '0002_groupmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='avatar_url',
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='group',
            name='invite_token',
            field=models.UUIDField(blank=True, db_index=True, null=True, unique=True, default=None),
        ),
    ]
