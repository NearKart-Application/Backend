"""
Increase referral_code max_length from 10 → 16 to accommodate the new
NS-<NN>-<AA>-<RRRR> code format (14 chars).
Also update referral_code on the Referral history table.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loyalty', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='loyaltyaccount',
            name='referral_code',
            field=models.CharField(max_length=16, unique=True),
        ),
        migrations.AlterField(
            model_name='referral',
            name='referral_code',
            field=models.CharField(max_length=16),
        ),
    ]
