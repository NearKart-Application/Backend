"""
Seeds test coupons for development/QA.
Run: python manage.py seed_coupons
"""
from django.core.management.base import BaseCommand
from apps.billing.models import Coupon, Plan


class Command(BaseCommand):
    help = 'Seed test discount coupons'

    def handle(self, *args, **kwargs):
        basic_plan   = Plan.objects.filter(name=Plan.SLUG_BASIC).first()
        premium_plan = Plan.objects.filter(name=Plan.SLUG_PREMIUM).first()

        coupons = [
            {
                'code':             'NEARSPOT100',
                'discount_percent': 100,
                'max_uses':         0,
                'plans':            [],   # empty = all plans
            },
            {
                'code':             'TESTBASIC',
                'discount_percent': 100,
                'max_uses':         0,
                'plans':            [basic_plan] if basic_plan else [],
            },
            {
                'code':             'TESTPREMIUM',
                'discount_percent': 100,
                'max_uses':         0,
                'plans':            [premium_plan] if premium_plan else [],
            },
        ]

        for data in coupons:
            plans = data.pop('plans')
            coupon, created = Coupon.objects.update_or_create(
                code=data['code'],
                defaults={**data, 'is_active': True},
            )
            if plans:
                coupon.applicable_plans.set(plans)
            else:
                coupon.applicable_plans.clear()
            status = 'created' if created else 'updated'
            self.stdout.write(self.style.SUCCESS(f'  {coupon.code} ({coupon.discount_percent}% off) — {status}'))

        self.stdout.write(self.style.SUCCESS('Coupons seeded successfully.'))
