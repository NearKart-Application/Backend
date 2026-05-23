"""
NearKart — Reservation Service
All business logic for creating, updating, and expiring reservations.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.notifications.services import NotificationService
from .models import Reservation, ReservationStatus

logger = logging.getLogger(__name__)


class ReservationService:

    @staticmethod
    def create(customer, store, product, quantity: int, note: str = '',
               points_redeemed: int = 0, discount_amount=0) -> Reservation:
        hold_hours = getattr(settings, 'RESERVATION_HOLD_HOURS', 2)
        expires_at = timezone.now() + timedelta(hours=hold_hours)
        reservation = Reservation.objects.create(
            customer=customer,
            store=store,
            product=product,
            quantity=quantity,
            note=note,
            expires_at=expires_at,
            points_redeemed=points_redeemed,
            discount_amount=discount_amount,
        )
        logger.info('[reservations] created %s — %s x%d', reservation.id, product.name, quantity)
        NotificationService.notify_reservation_created(
            store.owner,
            customer.full_name or customer.phone_number,
            str(reservation.id),
            product.name,
        )
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
        return reservation

    @staticmethod
    def cancel(reservation: Reservation, note: str = '') -> Reservation:
        reservation.status = ReservationStatus.CANCELLED
        if note:
            reservation.vendor_note = note
            reservation.save(update_fields=['status', 'vendor_note', 'updated_at'])
        else:
            reservation.save(update_fields=['status', 'updated_at'])
        logger.info('[reservations] cancelled %s', reservation.id)
        NotificationService.notify_reservation_cancelled(
            reservation.customer,
            reservation.store.name,
            str(reservation.id),
        )
        return reservation

    @staticmethod
    def complete(reservation: Reservation) -> Reservation:
        reservation.status = ReservationStatus.COMPLETED
        reservation.save(update_fields=['status', 'updated_at'])
        logger.info('[reservations] completed %s', reservation.id)
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
        return count

    @staticmethod
    def get_for_customer(customer):
        return Reservation.objects.filter(customer=customer).select_related(
            'store', 'product'
        ).order_by('-created_at')

    @staticmethod
    def get_for_store(store):
        return Reservation.objects.filter(store=store).select_related(
            'customer', 'product'
        ).order_by('-created_at')
