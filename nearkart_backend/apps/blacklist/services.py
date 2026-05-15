"""
NearKart — Blacklist Service
"""
from .models import Blacklist


class BlacklistService:

    @staticmethod
    def toggle(store, customer, reason=''):
        """Block if not blocked, unblock if already blocked. Returns (is_now_blocked, obj_or_None)."""
        existing = Blacklist.objects.filter(store=store, customer=customer).first()
        if existing:
            existing.delete()
            return False, None
        obj = Blacklist.objects.create(store=store, customer=customer, reason=reason)
        return True, obj

    @staticmethod
    def is_blocked(store, customer) -> bool:
        """True if customer is blacklisted by this store."""
        return Blacklist.objects.filter(store=store, customer=customer).exists()

    @staticmethod
    def list_for_store(store):
        return Blacklist.objects.filter(store=store).select_related('customer')
