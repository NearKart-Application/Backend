"""
NearKart — Billing Service
"""
from decimal import Decimal
from django.db import transaction as db_transaction
from django.utils import timezone
from datetime import timedelta

from apps.notifications.services import NotificationService
from .models import Plan, Subscription, Transaction


class BillingService:

    # ── Wallet ───────────────────────────────────────────────────────────────

    @staticmethod
    def topup(store, amount: Decimal, reference_id: str = '') -> Transaction:
        """Credit vendor wallet. Returns the Transaction record."""
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

    # ── Subscription ─────────────────────────────────────────────────────────

    @staticmethod
    def subscribe(store, plan: Plan) -> Subscription:
        """
        Deduct plan price from wallet and activate/upgrade the subscription.
        Free plan (price=0) never touches wallet balance.
        """
        if plan.price > 0 and store.wallet_balance < plan.price:
            raise ValueError(
                f'Insufficient wallet balance. '
                f'Need ₹{plan.price}, have ₹{store.wallet_balance}.'
            )

        with db_transaction.atomic():
            now = timezone.now()
            expires = now + timedelta(days=plan.duration_days)

            # Deduct from wallet (skip for free plan)
            if plan.price > 0:
                store.__class__.objects.filter(pk=store.pk).update(
                    wallet_balance=store.wallet_balance - plan.price
                )
                store.refresh_from_db(fields=['wallet_balance'])
                Transaction.objects.create(
                    store=store,
                    type=Transaction.TYPE_SUBSCRIPTION,
                    amount=-plan.price,
                    description=f'Subscribed to {plan.display_name}',
                    reference_id=f'SUB-{plan.name.upper()}-{int(now.timestamp())}',
                    balance_after=store.wallet_balance,
                )

            # Create or update subscription
            sub, _ = Subscription.objects.update_or_create(
                store=store,
                defaults={
                    'plan': plan,
                    'started_at': now,
                    'expires_at': expires,
                    'is_active': True,
                },
            )
            return sub

    # ── Query helpers ────────────────────────────────────────────────────────

    @staticmethod
    def get_active_plan(store) -> Plan:
        """Returns the store's current Plan, or the free plan if expired/none."""
        try:
            sub = store.subscription
            if sub.is_active and sub.expires_at > timezone.now():
                return sub.plan
        except Subscription.DoesNotExist:
            pass
        return Plan.objects.filter(name=Plan.SLUG_FREE).first()

    @staticmethod
    def get_subscription(store):
        """Returns Subscription or None."""
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
        """
        Returns (allowed, message).
        allowed=True means the vendor can upload another video.
        """
        plan = BillingService.get_active_plan(store)
        if plan is None or plan.video_limit == 0:
            return True, ''
        current = store.videos.filter(
            status__in=['pending_upload', 'processing', 'ready']
        ).count()
        if current >= plan.video_limit:
            return False, (
                f'Your {plan.display_name} allows {plan.video_limit} active video(s). '
                f'You have {current}. Upgrade your plan or delete an existing video.'
            )
        return True, ''

    @staticmethod
    def check_product_limit(store) -> tuple[bool, str]:
        """Returns (allowed, message)."""
        plan = BillingService.get_active_plan(store)
        if plan is None or plan.product_limit == 0:
            return True, ''
        current = store.products.filter(status__in=['active', 'draft', 'inactive']).count()
        if current >= plan.product_limit:
            return False, (
                f'Your {plan.display_name} allows {plan.product_limit} product(s). '
                f'You have {current}. Upgrade your plan or delete an existing product.'
            )
        return True, ''

    # ── Celery task helper ───────────────────────────────────────────────────

    @staticmethod
    def expire_overdue_subscriptions() -> int:
        """Marks all past-expiry active subscriptions as inactive. Returns count."""
        now = timezone.now()
        count = Subscription.objects.filter(
            is_active=True,
            expires_at__lt=now,
        ).update(is_active=False)
        return count
