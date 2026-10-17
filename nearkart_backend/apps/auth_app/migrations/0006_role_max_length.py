"""Increase role max_length from 10 → 12 to accommodate 'master_admin'."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0005_backfill_profile_id_ns'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(blank=True, choices=[('customer','Customer'),('vendor','Vendor'),('admin','Admin'),('master_admin','Master Admin')], default='', max_length=12),
        ),
    ]
