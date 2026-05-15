"""
Creates the 3 default NearKart subscription plans.
Run once after migration: docker compose exec django python manage.py seed_plans
"""
from django.core.management.base import BaseCommand
from apps.billing.models import Plan


PLANS = [
    {
        'name':          Plan.SLUG_FREE,
        'display_name':  'Free Plan',
        'price':         '0.00',
        'duration_days': 30,
        'video_limit':   3,
        'product_limit': 10,
        'description':   'Up to 3 videos and 10 products. No payment required.',
    },
    {
        'name':          Plan.SLUG_BASIC,
        'display_name':  'Basic Plan',
        'price':         '499.00',
        'duration_days': 30,
        'video_limit':   20,
        'product_limit': 50,
        'description':   'Up to 20 videos and 50 products. ₹499/month.',
    },
    {
        'name':          Plan.SLUG_PREMIUM,
        'display_name':  'Premium Plan',
        'price':         '999.00',
        'duration_days': 30,
        'video_limit':   0,
        'product_limit': 0,
        'description':   'Unlimited videos and products. ₹999/month.',
    },
]


class Command(BaseCommand):
    help = 'Seed default subscription plans (Free / Basic / Premium)'

    def handle(self, *args, **kwargs):
        created = 0
        updated = 0
        for data in PLANS:
            _, was_created = Plan.objects.update_or_create(
                name=data['name'],
                defaults=data,
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f'Plans seeded: {created} created, {updated} updated.'
            )
        )
