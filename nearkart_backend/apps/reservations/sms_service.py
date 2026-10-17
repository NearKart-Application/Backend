"""
NearKart — SMS Service for Reservations
Sends transactional SMS via MSG91 (or Twilio) when configured.
Set SMS_PROVIDER = 'msg91' | 'twilio' | 'disabled' in Django settings.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(to: str, message: str) -> bool:
    """Send SMS to `to` (E.164 format). Returns True on success."""
    provider = getattr(settings, 'SMS_PROVIDER', 'disabled')

    if provider == 'disabled' or not to:
        return False

    if provider == 'msg91':
        return _send_msg91(to, message)
    if provider == 'twilio':
        return _send_twilio(to, message)

    logger.warning('[sms] Unknown provider: %s', provider)
    return False


def _send_msg91(to: str, message: str) -> bool:
    try:
        import requests
        auth_key = getattr(settings, 'MSG91_AUTH_KEY', '')
        sender   = getattr(settings, 'MSG91_SENDER_ID', 'NRSPT')
        route    = getattr(settings, 'MSG91_ROUTE', '4')
        r = requests.get(
            'https://api.msg91.com/api/sendhttp.php',
            params={
                'authkey': auth_key,
                'mobiles': to.lstrip('+'),
                'message': message,
                'sender':  sender,
                'route':   route,
                'country': '91',
            },
            timeout=5,
        )
        if r.ok:
            return True
        logger.warning('[sms/msg91] non-200: %s', r.text[:200])
    except Exception:
        logger.exception('[sms/msg91] failed to send to %s', to)
    return False


def _send_twilio(to: str, message: str) -> bool:
    try:
        from twilio.rest import Client
        client = Client(
            getattr(settings, 'TWILIO_ACCOUNT_SID', ''),
            getattr(settings, 'TWILIO_AUTH_TOKEN', ''),
        )
        client.messages.create(
            body=message,
            from_=getattr(settings, 'TWILIO_FROM_NUMBER', ''),
            to=to,
        )
        return True
    except Exception:
        logger.exception('[sms/twilio] failed to send to %s', to)
    return False


def sms_reservation_created(customer_phone: str, product_name: str, store_name: str,
                             expires_at: str) -> None:
    msg = (
        f"NearSpot: Your reservation for {product_name} at {store_name} is confirmed. "
        f"Hold expires at {expires_at}. Reply STOP to opt out."
    )
    send_sms(customer_phone, msg)


def sms_reservation_confirmed(customer_phone: str, store_name: str) -> None:
    msg = (
        f"NearSpot: {store_name} has confirmed your reservation and is preparing your order. "
        f"Head over to pick it up!"
    )
    send_sms(customer_phone, msg)


def sms_reservation_cancelled(customer_phone: str, store_name: str, reason: str = '') -> None:
    reason_txt = f" Reason: {reason}" if reason else ''
    msg = f"NearSpot: Your reservation at {store_name} has been cancelled.{reason_txt}"
    send_sms(customer_phone, msg)
