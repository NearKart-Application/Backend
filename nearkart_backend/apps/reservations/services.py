"""
NearKart — Reservation Service
All business logic for creating, updating, and expiring reservations.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Reservation, ReservationStatus

logger = logging.getLogger(__name__)


class ReservationService:

    @staticmethod
    def create(customer, store, product, quantity: int, note: str = '') -> Reservation:
        hold_hours = getattr(settings, 'RESERVATION_HOLD_HOURS', 2)
        expires_at = timezone.now() + timedelta(hours=hold_hours)
        reservation = Reservation.objects.create(
            customer=customer,
            store=store,
            product=product,
            quantity=quantity,
            note=note,
            expires_at=expires_at,
        )
        logger.info('[reservations] created %s — %s x%d', reservation.id, product.name, quantity)
        return reservation

    @staticmethod
    def confirm(reservation: Reservation, vendor_note: str = '') -> Reservation:
        reservation.status = ReservationStatus.CONFIRMED
        reservation.vendor_note = vendor_note
        reservation.save(update_fields=['status', 'vendor_note', 'updated_at'])
        logger.info('[reservations] confirmed %s', reservation.id)
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
        return reservation

    @staticmethod
    def complete(reservation: Reservation) -> Reservation:
        reservation.status = ReservationStatus.COMPLETED
        reservation.save(update_fields=['status', 'updated_at'])
        logger.info('[reservations] completed %s', reservation.id)
        return reservation

    @staticmethod
    def expire_pending() -> int:
        count = Reservation.objects.filter(
            status=ReservationStatus.PENDING,
            expires_at__lt=timezone.now(),
        ).update(status=ReservationStatus.EXPIRED)
        if count:
            logger.info('[reservations] expired %d reservation(s)', count)
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
