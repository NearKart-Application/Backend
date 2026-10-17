"""
Creates the 3 default NearKart subscription plans.
Run once after migration: docker compose exec django python manage.py seed_plans
"""
from django.core.management.base import BaseCommand
from apps.billing.models import Plan


PLANS = [
    {
        'name':          Plan.SLUG_BASIC,
        'display_name':  'Basic Plan',
        'price':         '299.00',
        'duration_days': 30,
        'video_limit':   20,
        'product_limit': 0,
        'description':   'Full inventory, your own website, store on map, offer cards, customer chat, reservations, group deals and analytics.',
    },
    {
        'name':          Plan.SLUG_PREMIUM,
        'display_name':  'Premium Plan',
        'price':         '499.00',
        'duration_days': 30,
        'video_limit':   0,
        'product_limit': 0,
        'description':   'Everything in Basic plus verified badge, priority in search results, unlimited videos and advanced analytics.',
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
