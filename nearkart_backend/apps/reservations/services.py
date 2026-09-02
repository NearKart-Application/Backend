"""
NearKart — Reservation Service
All business logic for creating, updating, and expiring reservations.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.notifications.services import NotificationService
from apps.products.inventory_service import InventoryService
from .models import Reservation, ReservationStatus
from . import sms_service

logger = logging.getLogger(__name__)


class ReservationService:

    @staticmethod
    def create(customer, store, product, quantity: int, note: str = '',
               points_redeemed: int = 0, discount_amount=0, variant=None,
               hold_hours: int = None, pickup_time=None) -> Reservation:
        hold_hours = hold_hours or getattr(settings, 'RESERVATION_HOLD_HOURS', 2)
        expires_at = timezone.now() + timedelta(hours=hold_hours)

        # Deduct stock from the selected variant before creating the reservation
        if variant is not None:
            ok = InventoryService.deduct_for_reservation(variant, quantity)
            if not ok:
                raise ValueError('insufficient_stock')

        cost_snapshot = None
        if variant is not None and variant.cost_price is not None:
            cost_snapshot = variant.cost_price

        reservation = Reservation.objects.create(
            customer=customer,
            store=store,
            product=product,
            variant=variant,
            quantity=quantity,
            note=note,
            expires_at=expires_at,
            points_redeemed=points_redeemed,
            discount_amount=discount_amount,
            pickup_time=pickup_time,
            cost_price_at_sale=cost_snapshot,
        )
        logger.info('[reservations] created %s — %s x%d', reservation.id, product.name, quantity)
        NotificationService.notify_reservation_created(
            store.owner,
            customer.full_name or customer.phone_number,
            str(reservation.id),
            product.name,
        )
        try:
            phone = getattr(customer, 'phone_number', '') or ''
            if phone:
                expires_str = reservation.expires_at.strftime('%I:%M %p')
                sms_service.sms_reservation_created(phone, product.name, store.name, expires_str)
        except Exception:
            logger.exception('[reservations] sms_reservation_created failed')
        return reservation

    @staticmethod
    def confirm(reservation: Reservation, vendor_note: str = '') -> Reservation:
        reservation.status = ReservationStatus.CONFIRMED
        reservation.vendor_note = vendor_note
        reservation.save(update_fields=['status', 'vendor_note', 'updated_at'])
        logger.info('[reservations] confirmed %s', reservation.id)
        NotificationService.notify_reservation_confirmed(
            reservation.customer,
            reservation.store.name,
            str(reservation.id),
        )
        try:
            phone = getattr(reservation.customer, 'phone_number', '') or ''
            if phone:
                sms_service.sms_reservation_confirmed(phone, reservation.store.name)
        except Exception:
            logger.exception('[reservations] sms_reservation_confirmed failed')
        return reservation

    @staticmethod
    def cancel(reservation: Reservation, note: str = '', cancel_reason: str = '',
               cancelled_by: str = '') -> Reservation:
        reservation.status = ReservationStatus.CANCELLED
        update_fields = ['status', 'updated_at']
        if note:
            reservation.vendor_note = note
            update_fields.append('vendor_note')
        if cancel_reason:
            reservation.cancel_reason = cancel_reason
            update_fields.append('cancel_reason')
        if cancelled_by:
            reservation.cancelled_by = cancelled_by
            update_fields.append('cancelled_by')
        reservation.save(update_fields=update_fields)
        if reservation.variant_id:
            InventoryService.restore_for_reservation(
                reservation.variant, reservation.quantity, str(reservation.id)
            )
        logger.info('[reservations] cancelled %s', reservation.id)
        NotificationService.notify_reservation_cancelled(
            reservation.customer,
            reservation.store.name,
            str(reservation.id),
        )
        return reservation

    @staticmethod
    def complete(reservation: Reservation, actual_selling_price=None) -> Reservation:
        reservation.status = ReservationStatus.COMPLETED
        update_fields = ['status', 'updated_at']
        if actual_selling_price is not None:
            reservation.actual_selling_price = actual_selling_price
            update_fields.append('actual_selling_price')
        reservation.save(update_fields=update_fields)
        logger.info('[reservations] completed %s', reservation.id)
        try:
            from apps.billing.services import ReferralService
            ReferralService.handle_customer_reservation_completed(reservation.customer)
        except Exception:
            pass  # referral credit must never break reservation completion
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_reservation_completed(
                customer=reservation.customer,
                store_name=reservation.store.name,
                reservation_id=str(reservation.id),
                product_name=reservation.product.name,
            )
        except Exception:
            logger.exception('[reservations] notify_reservation_completed failed for %s', reservation.id)
        return reservation

    @staticmethod
    def expire_pending() -> int:
        now = timezone.now()
        to_expire = list(
            Reservation.objects.filter(
                status=ReservationStatus.PENDING,
                expires_at__lt=now,
            ).select_related('customer', 'store')
        )
        count = Reservation.objects.filter(
            status=ReservationStatus.PENDING,
            expires_at__lt=now,
        ).update(status=ReservationStatus.EXPIRED)
        if count:
            logger.info('[reservations] expired %d reservation(s)', count)
            for r in to_expire:
                NotificationService.notify_reservation_expired(r.customer, r.store.name, str(r.id))
                if r.variant_id:
                    InventoryService.restore_for_reservation(r.variant, r.quantity, str(r.id))
        return count

    @staticmethod
    def get_for_customer(customer):
        return Reservation.objects.filter(customer=customer).select_related(
            'store', 'product', 'variant', 'served_by', 'served_by__user'
        ).order_by('-created_at')

    @staticmethod
    def get_for_store(store):
        return Reservation.objects.filter(store=store).select_related(
            'customer', 'product', 'variant', 'served_by', 'served_by__user'
        ).order_by('-created_at')
