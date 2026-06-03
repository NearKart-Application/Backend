"""
Backfill all existing User.profile_id values to the NS-NN-AA-RRRR format.
"""
import re
import secrets
import string

from django.db import migrations

_CHARS = string.ascii_uppercase + string.digits


def _name_tag(name):
    name = name.strip().upper()
    if not name:
        return 'XX'
    words = name.split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0])[:2]
    return name[:2].ljust(2, 'X')


def _area_tag(area):
    clean = re.sub(r'[^A-Za-z]', '', area).upper()
    if not clean:
        return 'XX'
    return clean[:2].ljust(2, 'X')


def _make_code(name='', area=''):
    nn = _name_tag(name)
    aa = _area_tag(area)
    rr = ''.join(secrets.choice(_CHARS) for _ in range(6))
    return f'NS-{nn}-{aa}-{rr}'


def backfill_profile_ids(apps, schema_editor):
    User = apps.get_model('auth_app', 'User')
    used = set(User.objects.values_list('profile_id', flat=True))

    for user in User.objects.all():
        code = _make_code(name=user.full_name or '')
        while code in used:
            code = _make_code(name=user.full_name or '')
        used.discard(user.profile_id)
        used.add(code)
        User.objects.filter(pk=user.pk).update(profile_id=code)


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0004_profile_id_ns_format'),
    ]

    operations = [
        migrations.RunPython(backfill_profile_ids, migrations.RunPython.noop),
    ]
