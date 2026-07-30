"""
Nearspot — Inventory Celery Tasks
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='inventory.check_low_stock_all', max_retries=2, default_retry_delay=60)
def check_low_stock_all(self):
    """Every 6 hours: scan all active variants, fire low-stock alerts."""
    try:
        from apps.inventory.services import InventoryService
        from apps.products.models import ProductVariant
        from django.db.models import F
        variants = ProductVariant.objects.filter(
            product__status='active',
            stock_quantity__lte=F('low_stock_threshold'),
            stock_quantity__gt=0,
        ).select_related('product__store__owner')
        count = 0
        for variant in variants:
            InventoryService._notify_vendor_low_stock(variant)
            count += 1
        logger.info('[inventory] low stock check: alerted %d variants', count)
        return count
    except Exception as exc:
        logger.error('[inventory] check_low_stock_all failed, retrying: %s', exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, name='inventory.weekly_stock_summary', max_retries=1, default_retry_delay=120)
def weekly_stock_summary(self):
    """Monday 9AM IST: send weekly inventory digest to all active product vendors."""
    try:
        from apps.stores.models import Store
        from apps.notifications.services import NotificationService
        from apps.products.models import ProductStatus
        stores = Store.objects.filter(is_active=True, vendor_type='product').select_related('owner')
        for store in stores:
            low_count = store.products.filter(
                variants__stock_quantity__lte=5, variants__stock_quantity__gt=0
            ).distinct().count()
            oos_count = store.products.filter(status=ProductStatus.OUT_OF_STOCK).count()
            NotificationService.send(
                recipient=store.owner,
                notification_type='weekly_stock_summary',
                title='Your weekly inventory report',
                body=f'{low_count} low stock, {oos_count} out of stock products this week.',
                data={'low_count': low_count, 'oos_count': oos_count},
            )
    except Exception as exc:
        logger.error('[inventory] weekly_stock_summary failed, retrying: %s', exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, name='inventory.check_po_due_dates', max_retries=2, default_retry_delay=60)
def check_po_due_dates(self):
    """Daily 8AM IST: alert vendors with POs due tomorrow."""
    try:
        from apps.inventory.models import PurchaseOrder, PurchaseOrderStatus
        from apps.notifications.services import NotificationService
        tomorrow = (timezone.now() + timedelta(days=1)).date()
        overdue_pos = PurchaseOrder.objects.filter(
            expected_by=tomorrow,
            status=PurchaseOrderStatus.SENT
        ).select_related('store__owner', 'supplier')
        for po in overdue_pos:
            supplier_name = po.supplier.name if po.supplier else 'your supplier'
            NotificationService.send(
                recipient=po.store.owner,
                notification_type='po_reminder',
                title='Purchase order due tomorrow',
                body=f'PO from {supplier_name} is expected tomorrow. Mark as received or update the date.',
                data={'po_id': str(po.id)},
            )
    except Exception as exc:
        logger.error('[inventory] check_po_due_dates failed, retrying: %s', exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, name='inventory.reset_watchlist_notifications', max_retries=2, default_retry_delay=60)
def reset_watchlist_notifications(self):
    """Daily midnight: reset notified_at for products that went OOS again."""
    try:
        from apps.inventory.models import StockWatchlist
        from apps.products.models import ProductStatus
        reset_count = StockWatchlist.objects.filter(
            product__status=ProductStatus.OUT_OF_STOCK,
            notified_at__isnull=False
        ).update(notified_at=None)
        logger.info('[inventory] watchlist reset: %d entries reset', reset_count)
        return reset_count
    except Exception as exc:
        logger.error('[inventory] reset_watchlist_notifications failed, retrying: %s', exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, name='inventory.detect_dead_stock', max_retries=1, default_retry_delay=120)
def detect_dead_stock(self):
    """Weekly Sunday midnight: flag products with no stock movement in 30 days."""
    try:
        from apps.inventory.models import StockMovementLog
        from apps.products.models import Product
        from apps.notifications.services import NotificationService
        cutoff = timezone.now() - timedelta(days=30)
        active_product_ids = StockMovementLog.objects.filter(
            created_at__gte=cutoff
        ).values_list('variant__product_id', flat=True).distinct()
        dead_products = (
            Product.objects
            .filter(status='active')
            .exclude(id__in=active_product_ids)
            .select_related('store__owner')
        )
        count = 0
        notified_stores: set = set()
        for product in dead_products.iterator():
            count += 1
            store = product.store
            if store.id not in notified_stores:
                notified_stores.add(store.id)
                try:
                    NotificationService.send(
                        recipient=store.owner,
                        notification_type='dead_stock_alert',
                        title='Slow-moving products detected',
                        body=(
                            f'Some products in {store.name} have had no stock activity in 30+ days. '
                            'Consider running a sale or updating your inventory.'
                        ),
                        data={'store_id': str(store.id)},
                    )
                except Exception as notify_exc:
                    logger.warning('[inventory] dead_stock notify failed store %s: %s', store.id, notify_exc)
        logger.info(
            '[inventory] dead stock: %d products, %d stores notified', count, len(notified_stores)
        )
        return count
    except Exception as exc:
        logger.error('[inventory] detect_dead_stock failed, retrying: %s', exc)
        raise self.retry(exc=exc)
