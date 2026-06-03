"""
Increase profile_id max_length from 12 → 16 to accommodate the new
NS-<NN>-<AA>-<RRRR> code format (14 chars).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0003_allow_blank_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='profile_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                max_length=16,
                unique=True,
            ),
        ),
    ]
