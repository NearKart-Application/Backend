"""
Nearspot — Inventory Service
Handles stock updates, auto-status transitions, movement logging,
back-in-stock notifications, and low-stock alerts.
"""
import logging

from django.db import transaction
from django.db.models import Sum

from apps.notifications.services import NotificationService
from apps.products.models import (
    Product, ProductStatus, ProductVariant,
    StockMovementLog, StockMovementReason, StockWatchlist,
)

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = 5

# Only restore from these statuses — BLACKLISTED must not be auto-restored
RESTORABLE_STATUSES = {ProductStatus.OUT_OF_STOCK}


class InventoryService:

    @staticmethod
    @transaction.atomic
    def update_stock(variant: ProductVariant, new_qty: int, changed_by=None,
                     reason: str = StockMovementReason.MANUAL, note: str = '') -> ProductVariant:
        """Set absolute stock quantity for a variant, log the movement, and sync product status."""
        # Bug 1 fix: reject negative stock
        if new_qty < 0:
            raise ValueError(f'Stock quantity cannot be negative. Received: {new_qty}')

        old_qty  = variant.stock_quantity
        delta    = new_qty - old_qty
        was_zero = old_qty == 0

        variant.stock_quantity = new_qty
        variant.save(update_fields=['stock_quantity', 'updated_at'])

        StockMovementLog.objects.create(
            variant=variant, changed_by=changed_by,
            old_qty=old_qty, new_qty=new_qty, delta=delta,
            reason=reason, note=note,
        )

        InventoryService._sync_product_status(variant.product)

        # Back-in-stock: was 0, now > 0 → notify watchers
        if was_zero and new_qty > 0:
            InventoryService._notify_watchers(variant.product)

        # Low-stock alert to vendor — use per-variant threshold, not global constant
        if reason == StockMovementReason.MANUAL and 0 < new_qty <= variant.low_stock_threshold < old_qty:
            InventoryService._notify_vendor_low_stock(variant)

        # Bug 3 fix: reset blacklist timer on stock update
        from django.utils import timezone
        Product.objects.filter(pk=variant.product_id).update(last_updated_at=timezone.now())

        return variant

    @staticmethod
    @transaction.atomic
    def deduct_for_reservation(variant: ProductVariant, qty: int, reservation_id: str = '') -> bool:
        """
        Deduct stock when a reservation is placed.
        Returns False if insufficient stock.
        Uses select_for_update to prevent race conditions.
        """
        variant = ProductVariant.objects.select_for_update().get(pk=variant.pk)
        if variant.stock_quantity < qty:
            return False
        InventoryService.update_stock(
            variant=variant,
            new_qty=variant.stock_quantity - qty,
            reason=StockMovementReason.RESERVATION,
            note=f'reservation:{reservation_id}',
        )
        return True

    @staticmethod
    @transaction.atomic
    def restore_for_reservation(variant: ProductVariant, qty: int, reservation_id: str = '') -> None:
        """Restore stock when a reservation is cancelled or expired."""
        variant = ProductVariant.objects.select_for_update().get(pk=variant.pk)
        InventoryService.update_stock(
            variant=variant,
            new_qty=variant.stock_quantity + qty,
            reason=StockMovementReason.RESTORATION,
            note=f'reservation:{reservation_id}',
        )

    @staticmethod
    @transaction.atomic
    def deduct_for_invoice(product_id: str, qty: int, changed_by=None,
                           invoice_id: str = '', store=None, variant_id=None) -> bool:
        """
        Deduct qty from a product's variants when an invoice is created.
        Bug 6 fix: if variant_id is provided, deducts from that specific variant.
        Otherwise falls back to highest-stock-first cascade.
        """
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            logger.warning('[inventory] invoice deduct: product %s not found', product_id)
            return False

        if store is not None and product.store_id != store.id:
            logger.warning('[inventory] invoice deduct: product %s not owned by store %s', product_id, store.id)
            return False

        # Bug 6 fix: use specific variant when variant_id is provided
        if variant_id:
            try:
                variants = list(ProductVariant.objects.select_for_update().filter(pk=variant_id, product=product))
            except Exception:
                variants = []
        else:
            variants = list(
                ProductVariant.objects.select_for_update()
                .filter(product=product)
                .order_by('-stock_quantity')
            )

        if not variants:
            logger.warning('[inventory] invoice deduct: no suitable variant for product %s', product_id)
            return False

        remaining = qty
        for variant in variants:
            if remaining <= 0:
                break
            old_qty = variant.stock_quantity
            deduct  = min(remaining, old_qty)
            new_qty = old_qty - deduct
            variant.stock_quantity = new_qty
            variant.save(update_fields=['stock_quantity', 'updated_at'])
            StockMovementLog.objects.create(
                variant=variant, changed_by=changed_by,
                old_qty=old_qty, new_qty=new_qty, delta=-deduct,
                reason=StockMovementReason.INVOICE,
                note=f'invoice:{invoice_id}' if invoice_id else 'invoice sale',
            )
            remaining -= deduct

        InventoryService._sync_product_status(product)

        for variant in variants:
            if 0 < variant.stock_quantity <= variant.low_stock_threshold:
                InventoryService._notify_vendor_low_stock(variant)
                break

        if remaining > 0:
            logger.warning('[inventory] invoice deduct: shortfall of %d for product %s', remaining, product_id)
        return remaining == 0

    @staticmethod
    def _sync_product_status(product: Product) -> None:
        """
        Auto-set product status based on stock.
        Bug 2 fix: never override BLACKLISTED — only restore from OUT_OF_STOCK.
        """
        total_stock = product.variants.aggregate(total=Sum('stock_quantity'))['total'] or 0
        if total_stock == 0 and product.status == ProductStatus.ACTIVE:
            product.status = ProductStatus.OUT_OF_STOCK
            product.save(update_fields=['status', 'last_updated_at'])
            logger.info('[inventory] product %s → OUT_OF_STOCK', product.id)
        elif total_stock > 0 and product.status in RESTORABLE_STATUSES:
            product.status = ProductStatus.ACTIVE
            product.save(update_fields=['status', 'last_updated_at'])
            logger.info('[inventory] product %s → ACTIVE (restocked)', product.id)

    @staticmethod
    def _notify_watchers(product: Product) -> None:
        """Bug 4 fix: reset notified_at after notifying so customers can be re-notified on future OOS→back."""
        from django.utils import timezone
        watchers = StockWatchlist.objects.filter(product=product, notified_at__isnull=True).select_related('customer')
        for watch in watchers:
            NotificationService.notify_back_in_stock(
                customer=watch.customer,
                product_name=product.name,
                store_name=product.store.name,
                product_id=str(product.id),
            )
        # Bug 4 fix: mark notified so they won't be re-notified until product goes OOS again
        StockWatchlist.objects.filter(product=product, notified_at__isnull=True).update(notified_at=timezone.now())
        if watchers.exists():
            logger.info('[inventory] notified %d watcher(s) — product %s', watchers.count(), product.id)

    @staticmethod
    def _notify_vendor_low_stock(variant: ProductVariant) -> None:
        """Bug 5 fix: 24-hour cooldown to avoid spamming vendor with repeated low-stock alerts."""
        from django.utils import timezone
        from datetime import timedelta
        # Check cooldown via StockMovementLog note
        last_alert = StockMovementLog.objects.filter(
            variant=variant,
            note__startswith='low_stock_alert'
        ).order_by('-created_at').first()
        if last_alert and (timezone.now() - last_alert.created_at) < timedelta(hours=24):
            return  # cooldown active

        vendor = variant.product.store.owner
        NotificationService.send(
            recipient=vendor,
            notification_type='low_stock',
            title='Low stock alert',
            body=f'{variant.product.name} — {variant.name} has only {variant.stock_quantity} left.',
            data={
                'notification_type': 'low_stock',
                'product_id':        str(variant.product_id),
                'variant_id':        str(variant.id),
            },
        )
        # Log the alert for cooldown tracking
        StockMovementLog.objects.create(
            variant=variant, changed_by=None,
            old_qty=variant.stock_quantity, new_qty=variant.stock_quantity,
            delta=0, reason=StockMovementReason.MANUAL,
            note='low_stock_alert',
        )
