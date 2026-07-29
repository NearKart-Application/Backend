"""
NearKart — Loyalty Service
Award points, redeem points, apply referral codes.

Points config:
  Referral earn (customer referrer) : 50 pts
  Referral earn (vendor referrer)   : 100 pts
  10 points = ₹1 discount
  Min redeem per transaction        : 50 pts  (= ₹5)
  Max redeem per transaction        : 500 pts (= ₹50)
"""
import logging
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import LoyaltyAccount, LoyaltyTransaction, Referral

logger = logging.getLogger(__name__)

REFERRAL_PTS_CUSTOMER  = 50
REFERRAL_PTS_VENDOR    = 100
PICKUP_BONUS_POINTS    = 20   # awarded when customer completes a reservation pickup
POINTS_PER_RUPEE       = 10
MIN_REDEEM             = 50
MAX_REDEEM             = 500


class LoyaltyService:

    # ── Public API ───────────────────────────────────────────────────────────

    @classmethod
    def get_account(cls, user) -> LoyaltyAccount:
        return LoyaltyAccount.get_or_create_for(user)

    @classmethod
    def apply_referral(cls, user, referral_code: str) -> dict:
        """Called when a new user enters a referral code. Awards points to referrer."""
        code = referral_code.strip().upper()

        with transaction.atomic():
            # Lock the user row to prevent concurrent referral applications
            from apps.auth_app.models import User as _User
            _User.objects.select_for_update().get(pk=user.pk)

            # Already used a code?
            if Referral.objects.filter(referred=user, status=Referral.STATUS_COMPLETED).exists():
                raise ValueError('You have already applied a referral code.')

            # Resolve referrer by profile_id (the NS code IS the referral code)
            try:
                referrer_account = LoyaltyAccount.objects.get(user__profile_id=code)
            except LoyaltyAccount.DoesNotExist:
                raise ValueError('Invalid referral code. Please check and try again.')

            referrer = referrer_account.user
            if referrer == user:
                raise ValueError('You cannot use your own referral code.')

            # Points depend on referrer's role
            pts = REFERRAL_PTS_VENDOR if referrer.role == 'vendor' else REFERRAL_PTS_CUSTOMER

            # Record referral
            Referral.objects.create(
                referrer=referrer,
                referred=user,
                referral_code=code,
                status=Referral.STATUS_COMPLETED,
                points_awarded=pts,
                completed_at=timezone.now(),
            )

            # Credit referrer
            cls._add_points(
                account=referrer_account,
                points=pts,
                source=LoyaltyTransaction.SOURCE_REFERRAL,
                description=f'Referral bonus — {user.full_name or user.phone_number} joined NearSpot',
            )

            # Notify referrer
            cls._send_referral_notification(referrer, pts, user)

            logger.info('[loyalty] referral applied: %s → %s, %d pts', referrer.phone_number, user.phone_number, pts)
            return {'points_awarded': pts, 'referrer_phone': referrer.phone_number}

    @classmethod
    def redeem_points(cls, user, points: int, description: str = 'Reservation discount') -> int:
        """
        Deducts points from user balance.
        Returns discount amount in rupees (points // POINTS_PER_RUPEE).
        """
        if points < MIN_REDEEM:
            raise ValueError(f'Minimum redemption is {MIN_REDEEM} points (₹{MIN_REDEEM // POINTS_PER_RUPEE}).')
        if points > MAX_REDEEM:
            raise ValueError(f'Maximum redemption per transaction is {MAX_REDEEM} points (₹{MAX_REDEEM // POINTS_PER_RUPEE}).')

        with transaction.atomic():
            account = LoyaltyAccount.objects.select_for_update().get(
                pk=cls.get_account(user).pk
            )
            if account.balance < points:
                raise ValueError(f'Insufficient points. Balance: {account.balance} pts.')

            cls._deduct_points(account=account, points=points, source=LoyaltyTransaction.SOURCE_REDEMPTION, description=description)
        discount_rupees = points // POINTS_PER_RUPEE
        logger.info('[loyalty] redeemed %d pts (₹%d) for %s', points, discount_rupees, user.phone_number)
        return discount_rupees

    @classmethod
    def award_pickup_bonus(cls, user, description: str = 'Reservation pickup bonus') -> int:
        """Awards PICKUP_BONUS_POINTS when a customer completes a reservation pickup. Returns points awarded."""
        account = cls.get_account(user)
        cls._add_points(account=account, points=PICKUP_BONUS_POINTS,
                        source=LoyaltyTransaction.SOURCE_EARNED, description=description)
        logger.info('[loyalty] pickup bonus %d pts for %s', PICKUP_BONUS_POINTS, user.phone_number)
        return PICKUP_BONUS_POINTS

    @classmethod
    def deduct_cancellation_penalty(cls, user, points: int = 5, description: str = 'Reservation cancellation penalty') -> int:
        """
        Deducts penalty points when customer cancels a reservation.
        Deducts min(points, balance) so balance never goes negative.
        Returns actual points deducted (0 if balance already 0).
        """
        account = cls.get_account(user)
        if account.balance <= 0:
            return 0
        to_deduct = min(points, account.balance)
        cls._deduct_points(
            account=account,
            points=to_deduct,
            source=LoyaltyTransaction.SOURCE_PENALTY,
            description=description,
        )
        logger.info('[loyalty] penalty %d pts for %s (balance: %d)', to_deduct, user.phone_number, account.balance)
        return to_deduct

    # ── Internal ────────────────────────────────────────────────────────────

    @classmethod
    def _add_points(cls, account: LoyaltyAccount, points: int, source: str, description: str):
        LoyaltyAccount.objects.filter(pk=account.pk).update(
            balance=F('balance') + points,
            total_earned=F('total_earned') + points,
            updated_at=timezone.now(),
        )
        account.refresh_from_db(fields=['balance', 'total_earned'])
        LoyaltyTransaction.objects.create(
            account=account,
            transaction_type=LoyaltyTransaction.EARN,
            source=source,
            points=points,
            description=description,
            balance_after=account.balance,
        )

    @classmethod
    def _deduct_points(cls, account: LoyaltyAccount, points: int, source: str, description: str):
        LoyaltyAccount.objects.filter(pk=account.pk).update(
            balance=F('balance') - points,
            total_redeemed=F('total_redeemed') + points,
            updated_at=timezone.now(),
        )
        account.refresh_from_db(fields=['balance', 'total_redeemed'])
        LoyaltyTransaction.objects.create(
            account=account,
            transaction_type=LoyaltyTransaction.REDEEM,
            source=source,
            points=points,
            description=description,
            balance_after=account.balance,
        )

    @classmethod
    def _send_referral_notification(cls, referrer, pts: int, referred_user):
        try:
            from apps.notifications.services import NotificationService
            from apps.notifications.models import NotificationType
            name = referred_user.full_name or referred_user.phone_number
            NotificationService.send(
                recipient=referrer,
                notification_type=NotificationType.LOYALTY,
                title='Referral Bonus Earned! 🎉',
                body=f'You earned {pts} loyalty points! {name} joined NearSpot using your code.',
                data={'points': str(pts), 'source': 'referral'},
            )
        except Exception as e:
            logger.warning('[loyalty] notification failed: %s', e)
