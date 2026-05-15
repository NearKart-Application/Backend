import random
import string

from django.db import migrations, models


def _generate_unique_profile_ids(apps, schema_editor):
    User = apps.get_model('auth_app', 'User')
    chars = string.ascii_uppercase + string.digits
    used = set()
    for user in User.objects.filter(profile_id=''):
        while True:
            suffix = ''.join(random.choices(chars, k=8))
            pid = f'NK-{suffix}'
            if pid not in used:
                used.add(pid)
                break
        user.profile_id = pid
        user.save(update_fields=['profile_id'])


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0001_initial"),
    ]

    operations = [
        # Step 1: add field without unique (allows empty default for existing rows)
        migrations.AddField(
            model_name="user",
            name="profile_id",
            field=models.CharField(blank=True, default='', max_length=12),
        ),
        # Step 2: populate profile_id for all existing users
        migrations.RunPython(_generate_unique_profile_ids, migrations.RunPython.noop),
        # Step 3: now enforce unique + index
        migrations.AlterField(
            model_name="user",
            name="profile_id",
            field=models.CharField(blank=True, db_index=True, default='', max_length=12, unique=True),
        ),
    ]
