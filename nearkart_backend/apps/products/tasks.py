"""
NearKart — Product Celery Tasks
notify_price_drops: runs every 6 hours, sends push+in-app to customers who
wishlisted a product whose price just dropped.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='products.notify_price_drops', time_limit=300, soft_time_limit=270)
def notify_price_drops():
    from .models import Product
    from apps.notifications.services import NotificationService

    dropped = Product.objects.filter(
        previous_price__isnull=False,
        status='active',
        is_visible=True,
    ).select_related('store').prefetch_related('wishlisted_by__user')

    notified = 0
    for product in dropped:
        if product.base_price >= product.previous_price:
            continue
        customers = [w.user for w in product.wishlisted_by.select_related('user').all()]
        for customer in customers:
            try:
                NotificationService.notify_price_drop(
                    customer     = customer,
                    product_name = product.name,
                    product_id   = str(product.id),
                    old_price    = str(int(product.previous_price)),
                    new_price    = str(int(product.base_price)),
                )
                notified += 1
            except Exception as exc:
                logger.warning('[notify_price_drops] failed for product %s customer %s: %s',
                               product.id, customer.id, exc)

        # Clear previous_price so we don't re-notify on unchanged data
        Product.objects.filter(pk=product.pk).update(previous_price=None)

    logger.info('[products] sent %d price-drop notification(s)', notified)
    return {'notified': notified}
