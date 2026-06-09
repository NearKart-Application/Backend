"""
NearKart — Billing Service
"""
from decimal import Decimal
from django.db import transaction as db_transaction
from django.db.models import F
from django.utils import timezone
from datetime import timedelta

from apps.notifications.services import NotificationService
from .models import Coupon, Plan, Subscription, Transaction


class BillingService:

    # ── Wallet ───────────────────────────────────────────────────────────────

    @staticmethod
    def topup(store, amount: Decimal, reference_id: str = '') -> Transaction:
        if amount <= 0:
            raise ValueError('Top-up amount must be positive.')
        with db_transaction.atomic():
            store.__class__.objects.filter(pk=store.pk).update(
                wallet_balance=store.wallet_balance + amount
            )
            store.refresh_from_db(fields=['wallet_balance'])
            txn = Transaction.objects.create(
                store=store,
                type=Transaction.TYPE_TOPUP,
                amount=amount,
                description=f'Wallet top-up of ₹{amount}',
                reference_id=reference_id or f'DEV-TOPUP-{int(timezone.now().timestamp())}',
                balance_after=store.wallet_balance,
            )
        NotificationService.notify_wallet_topup(store.owner, str(amount))
        return txn

    # ── Coupon ────────────────────────────────────────────────────────────────

    @staticmethod
    def validate_coupon(code: str, plan: Plan):
        """Returns (coupon, error_message). coupon is None if invalid."""
        try:
            coupon = Coupon.objects.get(code=code.strip().upper(), is_active=True)
        except Coupon.DoesNotExist:
            return None, 'Invalid coupon code.'

        if coupon.expires_at and coupon.expires_at < timezone.now():
            return None, 'This coupon has expired.'

        if coupon.max_uses > 0 and coupon.used_count >= coupon.max_uses:
            return None, 'This coupon has reached its usage limit.'

        if coupon.applicable_plans.exists() and not coupon.applicable_plans.filter(pk=plan.pk).exists():
            return None, f'This coupon is not valid for {plan.display_name}.'

        return coupon, ''

    @staticmethod
    def apply_discount(price: Decimal, coupon) -> Decimal:
        if coupon is None:
            return price
        discount = (price * coupon.discount_percent) / 100
        return max(price - discount, Decimal('0.00'))

    # ── Subscription ─────────────────────────────────────────────────────────

    @staticmethod
    def subscribe(store, plan: Plan, coupon=None) -> Subscription:
        final_price = BillingService.apply_discount(plan.price, coupon)

        if final_price > 0 and store.wallet_balance < final_price:
            raise ValueError(
                f'Insufficient wallet balance. '
                f'Need ₹{final_price}, have ₹{store.wallet_balance}.'
            )

        with db_transaction.atomic():
            now     = timezone.now()
            expires = now + timedelta(days=plan.duration_days)

            if final_price > 0:
                store.__class__.objects.filter(pk=store.pk).update(
                    wallet_balance=store.wallet_balance - final_price
                )
                store.refresh_from_db(fields=['wallet_balance'])
                coupon_note = f' (coupon: {coupon.code})' if coupon else ''
                Transaction.objects.create(
                    store=store,
                    type=Transaction.TYPE_SUBSCRIPTION,
                    amount=-final_price,
                    description=f'Subscribed to {plan.display_name}{coupon_note}',
                    reference_id=f'SUB-{plan.name.upper()}-{int(now.timestamp())}',
                    balance_after=store.wallet_balance,
                )

            if coupon:
                Coupon.objects.filter(pk=coupon.pk).update(used_count=F('used_count') + 1)

            # Sync verified badge with plan
            from apps.stores.models import Store as StoreModel
            StoreModel.objects.filter(pk=store.pk).update(
                is_verified=(plan.name == Plan.SLUG_PREMIUM)
            )

            sub, _ = Subscription.objects.update_or_create(
                store=store,
                defaults={
                    'plan':       plan,
                    'started_at': now,
                    'expires_at': expires,
                    'is_active':  True,
                },
            )
            return sub

    # ── Query helpers ────────────────────────────────────────────────────────

    @staticmethod
    def get_active_plan(store):
        """Returns the store's current active Plan, or None if no subscription."""
        try:
            sub = store.subscription
            if sub.is_active and sub.expires_at > timezone.now():
                return sub.plan
        except Subscription.DoesNotExist:
            pass
        return None

    @staticmethod
    def has_active_subscription(store) -> bool:
        return BillingService.get_active_plan(store) is not None

    @staticmethod
    def get_subscription(store):
        try:
            return store.subscription
        except Subscription.DoesNotExist:
            return None

    @staticmethod
    def get_transactions(store):
        return Transaction.objects.filter(store=store).order_by('-created_at')

    # ── Plan limits ──────────────────────────────────────────────────────────

    @staticmethod
    def check_video_limit(store) -> tuple[bool, str]:
        plan = BillingService.get_active_plan(store)
        if plan is None:
            return False, 'An active subscription is required to upload videos. Please subscribe to a plan.'
        if plan.video_limit == 0:
            return True, ''
        current = store.videos.filter(
            status__in=['pending_upload', 'processing', 'ready']
        ).count()
        if current >= plan.video_limit:
            return False, (
                f'Your {plan.display_name} allows {plan.video_limit} video(s). '
                f'You currently have {current}. Upgrade your plan or delete an existing video.'
            )
        return True, ''

    @staticmethod
    def check_product_limit(store) -> tuple[bool, str]:
        plan = BillingService.get_active_plan(store)
        if plan is None:
            return False, 'An active subscription is required to add products. Please subscribe to a plan.'
        if plan.product_limit == 0:
            return True, ''
        current = store.products.filter(status__in=['active', 'draft', 'inactive']).count()
        if current >= plan.product_limit:
            return False, (
                f'Your {plan.display_name} allows {plan.product_limit} product(s). '
                f'You currently have {current}. Upgrade your plan or delete an existing product.'
            )
        return True, ''

    # ── Celery task helper ───────────────────────────────────────────────────

    @staticmethod
    def expire_overdue_subscriptions() -> int:
        now = timezone.now()
        expired_subs = Subscription.objects.filter(
            is_active=True,
            expires_at__lt=now,
        ).select_related('store')

        count = 0
        for sub in expired_subs:
            sub.is_active = False
            sub.save(update_fields=['is_active'])
            # Remove verified badge when subscription expires
            from apps.stores.models import Store as StoreModel
            StoreModel.objects.filter(pk=sub.store.pk).update(is_verified=False)
            count += 1
        return count
