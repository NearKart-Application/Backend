"""
NearKart — Auth Celery Tasks
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_otp_sms(self, phone_number: str, otp: str):
    from apps.notifications.services import SMSService
    success = SMSService.send_otp(phone_number, otp)
    if not success:
        raise self.retry(exc=Exception(f'SMS delivery failed for {phone_number}'))
