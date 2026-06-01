"""
NearKart — Inventory Service
Handles stock updates, auto-status transitions, movement logging,
and back-in-stock notifications.
"""
import logging

from django.db import transaction
from django.db.models import Sum

from apps.notifications.services import NotificationService
from .models import (
    Product, ProductStatus, ProductVariant,
    StockMovementLog, StockMovementReason, StockWatchlist,
)

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = 5


class InventoryService:

    @staticmethod
    @transaction.atomic
    def update_stock(variant: ProductVariant, new_qty: int, changed_by=None,
                     reason: str = StockMovementReason.MANUAL, note: str = '') -> ProductVariant:
        """Set absolute stock quantity for a variant, log the movement, and sync product status."""
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

        # Low-stock alert to vendor (only on manual reductions that cross the threshold)
        if reason == StockMovementReason.MANUAL and 0 < new_qty <= LOW_STOCK_THRESHOLD < old_qty:
            InventoryService._notify_vendor_low_stock(variant)

        return variant

    @staticmethod
    @transaction.atomic
    def deduct_for_reservation(variant: ProductVariant, qty: int, reservation_id: str = '') -> bool:
        """
        Deduct stock when a reservation is placed.
        Returns False if insufficient stock (caller should reject the reservation).
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
                           invoice_id: str = '', store=None) -> bool:
        """
        Deduct qty from a product's variants when an invoice is created.
        Deducts from the highest-stock variant first, then cascades to others.
        Allows over-sell (goes to 0) so the invoice is never blocked — but logs
        everything so the vendor can see their actual position.
        Returns True if stock was fully satisfied, False if there was a shortfall.
        """
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            logger.warning('[inventory] invoice deduct: product %s not found', product_id)
            return False

        # Security: product must belong to the vendor's store
        if store is not None and product.store_id != store.id:
            logger.warning('[inventory] invoice deduct: product %s not owned by store %s', product_id, store.id)
            return False

        variants = list(
            ProductVariant.objects.select_for_update()
            .filter(product=product)
            .order_by('-stock_quantity')
        )
        if not variants:
            logger.warning('[inventory] invoice deduct: product %s has no variants', product_id)
            return False

        remaining = qty
        for variant in variants:
            if remaining <= 0:
                break
            old_qty   = variant.stock_quantity
            deduct    = min(remaining, old_qty)
            new_qty   = old_qty - deduct
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

        # Notify vendor if any variant crossed the low-stock threshold
        for variant in variants:
            if 0 < variant.stock_quantity <= LOW_STOCK_THRESHOLD:
                InventoryService._notify_vendor_low_stock(variant)
                break

        if remaining > 0:
            logger.warning('[inventory] invoice deduct: shortfall of %d for product %s', remaining, product_id)
        return remaining == 0

    @staticmethod
    def _sync_product_status(product: Product) -> None:
        """Auto-set product to OUT_OF_STOCK if all variants have stock=0, else restore ACTIVE."""
        total_stock = product.variants.aggregate(total=Sum('stock_quantity'))['total'] or 0
        if total_stock == 0 and product.status == ProductStatus.ACTIVE:
            product.status = ProductStatus.OUT_OF_STOCK
            product.save(update_fields=['status', 'last_updated_at'])
            logger.info('[inventory] product %s → OUT_OF_STOCK', product.id)
        elif total_stock > 0 and product.status == ProductStatus.OUT_OF_STOCK:
            product.status = ProductStatus.ACTIVE
            product.save(update_fields=['status', 'last_updated_at'])
            logger.info('[inventory] product %s → ACTIVE (restocked)', product.id)

    @staticmethod
    def _notify_watchers(product: Product) -> None:
        watchers = StockWatchlist.objects.filter(product=product).select_related('customer')
        for watch in watchers:
            NotificationService.send(
                recipient=watch.customer,
                notification_type='back_in_stock',
                title='Back in stock!',
                body=f'{product.name} is available again at {product.store.name}.',
                data={
                    'notification_type': 'back_in_stock',
                    'product_id':        str(product.id),
                    'store_id':          str(product.store_id),
                },
            )
        if watchers.exists():
            logger.info('[inventory] notified %d watcher(s) — product %s', watchers.count(), product.id)

    @staticmethod
    def _notify_vendor_low_stock(variant: ProductVariant) -> None:
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
