"""
NearKart — Billing Service
"""
import secrets
from decimal import Decimal
from django.db import transaction as db_transaction
from django.db.models import F
from django.utils import timezone
from datetime import timedelta

from apps.notifications.services import NotificationService
from .models import (
    Coupon, CouponRedemption, Plan, Subscription, Transaction,
    ReferralConfig, ReferralCode, UserReferralLink, VendorReferral,
)


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
    def validate_coupon(code: str, plan: Plan, store=None):
        """Returns (coupon, error_message). coupon is None if invalid.
        Pass store to enforce vendor-specific targeting.
        """
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

        # Vendor-specific: only the targeted store can use it
        if coupon.target_store_id is not None:
            if store is None or coupon.target_store_id != store.pk:
                return None, 'This coupon is not valid for your store.'

        return coupon, ''

    @staticmethod
    def apply_discount(price: Decimal, coupon) -> Decimal:
        if coupon is None:
            return price
        discount = (price * coupon.discount_percent) / 100
        return max(price - discount, Decimal('0.00'))

    # ── Subscription ─────────────────────────────────────────────────────────

    WALLET_DISCOUNT_CAP = Decimal('0.15')   # vendors can use up to 15% of plan price from wallet

    @staticmethod
    def calc_wallet_max(plan_price: Decimal) -> Decimal:
        return (plan_price * BillingService.WALLET_DISCOUNT_CAP).quantize(Decimal('0.01'))

    @staticmethod
    def subscribe(store, plan: Plan, coupon=None, wallet_discount: Decimal = Decimal('0'),
                  razorpay_payment_id: str = '') -> Subscription:
        after_coupon = BillingService.apply_discount(plan.price, coupon)

        # Clamp wallet_discount to the 15% cap and available balance
        max_wallet = BillingService.calc_wallet_max(plan.price)
        wallet_discount = max(Decimal('0'), min(wallet_discount, max_wallet, store.wallet_balance))

        final_price = max(after_coupon - wallet_discount, Decimal('0'))

        with db_transaction.atomic():
            now     = timezone.now()
            expires = now + timedelta(days=plan.duration_days)

            # Deduct wallet discount (separate transaction for transparency)
            if wallet_discount > 0:
                store.__class__.objects.filter(pk=store.pk).update(
                    wallet_balance=F('wallet_balance') - wallet_discount
                )
                store.refresh_from_db(fields=['wallet_balance'])
                Transaction.objects.create(
                    store=store,
                    type=Transaction.TYPE_SUBSCRIPTION,
                    amount=-wallet_discount,
                    description=f'Wallet discount for {plan.display_name} (15% cap)',
                    reference_id=f'WALLET-{plan.name.upper()}-{int(now.timestamp())}',
                    balance_after=store.wallet_balance,
                )

            # Record Razorpay payment if applicable
            if razorpay_payment_id and final_price > 0:
                coupon_note = f' + coupon {coupon.code}' if coupon else ''
                wallet_note = f' + ₹{wallet_discount} wallet' if wallet_discount > 0 else ''
                Transaction.objects.create(
                    store=store,
                    type=Transaction.TYPE_SUBSCRIPTION,
                    amount=-final_price,
                    description=f'{plan.display_name} via Razorpay{coupon_note}{wallet_note}',
                    reference_id=razorpay_payment_id,
                    balance_after=store.wallet_balance,
                )

            if coupon:
                Coupon.objects.filter(pk=coupon.pk).update(used_count=F('used_count') + 1)

            # Sync verified badge with plan — only grant on Premium; never forcibly revoke on downgrade
            from apps.stores.models import Store as StoreModel
            if plan.name == Plan.SLUG_PREMIUM:
                StoreModel.objects.filter(pk=store.pk).update(is_verified=True)

            sub, _ = Subscription.objects.update_or_create(
                store=store,
                defaults={
                    'plan':       plan,
                    'started_at': now,
                    'expires_at': expires,
                    'is_active':  True,
                },
            )

            # Audit trail for coupon redemptions
            if coupon:
                original = plan.price
                given    = original - after_coupon
                CouponRedemption.objects.create(
                    coupon=coupon,
                    store=store,
                    subscription=sub,
                    plan_name=plan.name,
                    plan_display=plan.display_name,
                    original_price=original,
                    discount_given=given,
                    price_paid=final_price,
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

    # ── Referral helpers ─────────────────────────────────────────────────

    @staticmethod
    def credit_referral_reward(store, amount: Decimal, reference_id: str = '') -> Transaction:
        with db_transaction.atomic():
            store.__class__.objects.filter(pk=store.pk).update(
                wallet_balance=F('wallet_balance') + amount
            )
            store.refresh_from_db(fields=['wallet_balance'])
            return Transaction.objects.create(
                store=store,
                type=Transaction.TYPE_REFERRAL,
                amount=amount,
                description=f'Referral reward of ₹{amount}',
                reference_id=reference_id,
                balance_after=store.wallet_balance,
            )

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


class ReferralService:

    @staticmethod
    def get_or_create_code(store) -> ReferralCode:
        # Return existing code if one already exists for this store
        try:
            return ReferralCode.objects.get(store=store)
        except ReferralCode.DoesNotExist:
            pass
        # Generate a collision-free code with a retry loop
        for _ in range(10):
            code = 'NSR' + secrets.token_hex(4).upper()  # e.g. NSRA1B2C3D4E
            obj, created = ReferralCode.objects.get_or_create(
                store=store, defaults={'code': code}
            )
            if created:
                return obj
            # Another request created the code concurrently — return it
            return obj
        raise ValueError('Could not generate unique referral code after 10 attempts')

    @staticmethod
    def get_config(city: str = '') -> ReferralConfig:
        """City config falls back to global (city='') if not found."""
        if city:
            try:
                return ReferralConfig.objects.get(city__iexact=city)
            except ReferralConfig.DoesNotExist:
                pass
        obj, _ = ReferralConfig.objects.get_or_create(city='')
        return obj

    @staticmethod
    def link_referred_user(user, referral_code: str):
        """Called at signup. Links user to referrer store. Silent on invalid code."""
        if not referral_code:
            return
        if UserReferralLink.objects.filter(user=user).exists():
            return
        try:
            ref = ReferralCode.objects.select_related('store').get(
                code=referral_code.strip().upper()
            )
        except ReferralCode.DoesNotExist:
            return
        if hasattr(user, 'stores') and user.stores.filter(pk=ref.store.pk).exists():
            return
        reward_type = (
            UserReferralLink.REWARD_VENDOR
            if user.role == 'vendor'
            else UserReferralLink.REWARD_CUSTOMER
        )
        UserReferralLink.objects.create(
            user=user,
            referrer_store=ref.store,
            reward_type=reward_type,
        )

    @staticmethod
    def handle_vendor_subscribed(vendor_user):
        """Credit referrer when vendor activates their FIRST subscription."""
        try:
            link = UserReferralLink.objects.select_related('referrer_store__owner').get(
                user=vendor_user,
                reward_credited=False,
            )
        except UserReferralLink.DoesNotExist:
            return
        sub_count = Subscription.objects.filter(store__owner=vendor_user).count()
        if sub_count > 1:
            return
        # Correct reward_type — new users have empty role at OTP time so it may be wrong
        if link.reward_type != UserReferralLink.REWARD_VENDOR:
            UserReferralLink.objects.filter(pk=link.pk).update(reward_type=UserReferralLink.REWARD_VENDOR)
            link.reward_type = UserReferralLink.REWARD_VENDOR
        city   = getattr(vendor_user, 'location_city', '') or ''
        config = ReferralService.get_config(city)
        ReferralService._credit(link, config.vendor_reward)

    @staticmethod
    def handle_customer_reservation_completed(customer):
        """Credit referrer when customer completes their FIRST reservation."""
        try:
            link = UserReferralLink.objects.select_related('referrer_store__owner').get(
                user=customer,
                reward_credited=False,
            )
        except UserReferralLink.DoesNotExist:
            return
        from apps.reservations.models import Reservation, ReservationStatus
        if Reservation.objects.filter(customer=customer, status=ReservationStatus.COMPLETED).count() != 1:
            return
        # Correct reward_type for the same reason as handle_vendor_subscribed
        if link.reward_type != UserReferralLink.REWARD_CUSTOMER:
            UserReferralLink.objects.filter(pk=link.pk).update(reward_type=UserReferralLink.REWARD_CUSTOMER)
            link.reward_type = UserReferralLink.REWARD_CUSTOMER
        city   = getattr(customer, 'location_city', '') or ''
        config = ReferralService.get_config(city)
        ReferralService._credit(link, config.customer_reward)

    @staticmethod
    def _credit(link: UserReferralLink, amount: Decimal):
        store = link.referrer_store
        with db_transaction.atomic():
            txn = BillingService.credit_referral_reward(
                store, amount, reference_id=f'REF-{link.id}'
            )
            VendorReferral.objects.create(
                referrer_store=store,
                referred_user=link.user,
                reward_type=link.reward_type,
                reward_amount=amount,
                transaction=txn,
            )
            UserReferralLink.objects.filter(pk=link.pk).update(reward_credited=True)
        NotificationService.notify_referral_reward(
            store.owner, str(amount), link.reward_type
        )
