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

    marked_oos = restored = 0

    for product in products:
        total = product.total_stock or 0
        if total == 0 and product.status != ProductStatus.OUT_OF_STOCK:
            Product.objects.filter(pk=product.pk).update(status=ProductStatus.OUT_OF_STOCK)
            marked_oos += 1
        elif total > 0 and product.status == ProductStatus.OUT_OF_STOCK:
            # Stock has been restocked — bring it back to active
            Product.objects.filter(pk=product.pk).update(status=ProductStatus.ACTIVE)
            restored += 1

    logger.info('[blacklist] product stock check: marked_oos=%d restored=%d', marked_oos, restored)
    return {'marked_out_of_stock': marked_oos, 'restored': restored}
