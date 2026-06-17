"""
NearKart — Blacklist Celery Tasks
check_inactive_products: runs at midnight daily, auto-marks out-of-stock products.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='blacklist.check_inactive_products')
def check_inactive_products():
    """
    Runs at midnight daily via Celery Beat.
    For every active product where ALL variants have stock_quantity=0,
    set status=out_of_stock. Products with at least one stocked variant stay active.
    Already-inactive or draft products are not touched.
    """
    from django.db.models import Sum
    from apps.products.models import Product, ProductStatus

    # Products that are currently active/out_of_stock and have zero total stock
    active_statuses = [ProductStatus.ACTIVE, ProductStatus.OUT_OF_STOCK]

    products = Product.objects.filter(
        status__in=active_statuses,
    ).annotate(
        total_stock=Sum('variants__stock_quantity'),
    )

    to_oos_ids    = []
    to_active_ids = []

    for product in products:
        total = product.total_stock or 0
        if total == 0 and product.status != ProductStatus.OUT_OF_STOCK:
            to_oos_ids.append(product.pk)
        elif total > 0 and product.status == ProductStatus.OUT_OF_STOCK:
            to_active_ids.append(product.pk)

    if to_oos_ids:
        Product.objects.filter(pk__in=to_oos_ids).update(status=ProductStatus.OUT_OF_STOCK)
    if to_active_ids:
        Product.objects.filter(pk__in=to_active_ids).update(status=ProductStatus.ACTIVE)

    marked_oos = len(to_oos_ids)
    restored   = len(to_active_ids)
    logger.info('[blacklist] product stock check: marked_oos=%d restored=%d', marked_oos, restored)
    return {'marked_out_of_stock': marked_oos, 'restored': restored}
