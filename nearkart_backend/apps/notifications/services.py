"""
NearKart — Notification Services
SMSService: OTP delivery via Twilio
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:

    @staticmethod
    def send_otp(phone_number: str, otp: str) -> bool:
        """
        Sends OTP SMS via Twilio. Returns True on success.
        Logs and returns False on failure without raising.
        """
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=f'Your NearKart OTP is {otp}. Valid for 5 minutes. Do not share.',
                from_=settings.TWILIO_FROM_NUMBER,
                to=phone_number,
            )
            logger.info(f'OTP SMS sent to {phone_number}')
            return True
        except Exception as e:
            logger.error(f'Failed to send OTP SMS to {phone_number}: {e}')
            return False
