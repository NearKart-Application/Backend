"""
NearKart — Reservation Celery Tasks
expire_reservations: runs hourly, marks stale pending holds as expired.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='reservations.expire_reservations', time_limit=300, soft_time_limit=270)
def expire_reservations():
    from .services import ReservationService
    count = ReservationService.expire_pending()
    logger.info('[reservations] expired %d reservation(s)', count)
    return {'expired': count}
