"""
Remove referral_code from LoyaltyAccount.
The user's profile_id (NS code) is the single unique identifier and
serves as the referral code — no separate field needed.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('loyalty', '0002_referral_code_ns_format'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='loyaltyaccount',
            name='referral_code',
        ),
    ]
