"""
NearKart — Razorpay Payment Service
Dev mode: skips real API calls, returns mock data.
Production: uses razorpay SDK with real keys.

Replace RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET in .env
with real credentials from https://dashboard.razorpay.com/app/keys
"""
import hashlib
import hmac
import logging
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger(__name__)


def _is_dev() -> bool:
    return 'PLACEHOLDER' in settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_ID


class RazorpayService:

    @staticmethod
    def create_order(amount_inr: Decimal, receipt: str, notes: dict = None) -> dict:
        """
        Creates a Razorpay order.
        Returns order dict with id, amount (paise), currency.
        """
        amount_paise = int(amount_inr * 100)

        if _is_dev():
            logger.info(f'[Razorpay-DEV] create_order receipt={receipt} amount=₹{amount_inr}')
            return {
                'id':       f'order_DEV_{receipt[:16]}',
                'amount':   amount_paise,
                'currency': 'INR',
                'receipt':  receipt,
                'status':   'created',
            }

        import razorpay
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        return client.order.create({
            'amount':   amount_paise,
            'currency': 'INR',
            'receipt':  receipt,
            'notes':    notes or {},
        })

    @staticmethod
    def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verifies the HMAC-SHA256 signature from Razorpay checkout callback.
        Returns True if signature is valid.
        """
        if _is_dev():
            logger.info(f'[Razorpay-DEV] verify_payment order={order_id} payment={payment_id}')
            return True

        msg = f'{order_id}|{payment_id}'.encode()
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            msg,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def verify_webhook_signature(body: bytes, signature: str) -> bool:
        """
        Verifies Razorpay webhook X-Razorpay-Signature header.
        Returns True if valid.
        """
        if _is_dev():
            return True

        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
