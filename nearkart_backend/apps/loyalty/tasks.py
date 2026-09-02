"""Loyalty background tasks."""
import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='loyalty.expire_points')
def expire_points():
    """Expire loyalty points whose expires_at has passed. Runs daily."""
    from .models import LoyaltyTransaction, LoyaltyAccount

    now = timezone.now()
    expired_tx_ids = list(
        LoyaltyTransaction.objects.filter(
            transaction_type=LoyaltyTransaction.EARN,
            is_expired=False,
            expires_at__lte=now,
        ).values_list('id', flat=True)
    )

    count = 0
    for tx_id in expired_tx_ids:
        try:
            with transaction.atomic():
                tx = (
                    LoyaltyTransaction.objects
                    .select_for_update(skip_locked=True)
                    .filter(id=tx_id, is_expired=False)
                    .select_related('account')
                    .first()
                )
                if tx is None:
                    continue  # already processed by another worker
                tx.is_expired = True
                tx.save(update_fields=['is_expired'])
                account = LoyaltyTransaction.objects.select_related('account').get(pk=tx_id).account
                account = LoyaltyAccount.objects.select_for_update().get(pk=account.pk)
                account.balance = max(0, account.balance - tx.points)
                account.save(update_fields=['balance'])
                LoyaltyTransaction.objects.create(
                    account=account,
                    transaction_type=LoyaltyTransaction.REDEEM,
                    source=LoyaltyTransaction.SOURCE_PENALTY,
                    points=tx.points,
                    description=f'Points expired (earned {tx.created_at.date()})',
                    balance_after=account.balance,
                )
                count += 1
        except Exception:
            logger.exception('[loyalty] expire_points failed for tx %s', tx_id)

    logger.info('[loyalty] expired %d point transactions', count)
    return {'expired': count}
