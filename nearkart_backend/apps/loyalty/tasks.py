"""Loyalty background tasks."""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='loyalty.expire_points')
def expire_points():
    """Expire loyalty points whose expires_at has passed. Runs daily."""
    from .models import LoyaltyTransaction, LoyaltyAccount

    now = timezone.now()
    expired_txs = LoyaltyTransaction.objects.filter(
        transaction_type=LoyaltyTransaction.EARN,
        is_expired=False,
        expires_at__lte=now,
    ).select_related('account')

    count = 0
    for tx in expired_txs:
        tx.is_expired = True
        tx.save(update_fields=['is_expired'])
        # Deduct from account balance (floor at 0)
        account = tx.account
        account.balance = max(0, account.balance - tx.points)
        account.save(update_fields=['balance'])
        # Record expiry transaction
        LoyaltyTransaction.objects.create(
            account=account,
            transaction_type=LoyaltyTransaction.REDEEM,
            source=LoyaltyTransaction.SOURCE_PENALTY,
            points=tx.points,
            description=f'Points expired (earned {tx.created_at.date()})',
            balance_after=account.balance,
        )
        count += 1

    logger.info('[loyalty] expired %d point transactions', count)
    return {'expired': count}
