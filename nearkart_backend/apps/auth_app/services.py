"""
NearKart — Auth Services
OTPService: generate/verify OTP
JWTService: issue access+refresh tokens with role claims
"""
import random
import logging
from django.contrib.gis.geos import Point

from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, OTPToken, UserRole

logger = logging.getLogger(__name__)


class OTPService:

    @staticmethod
    def generate_otp() -> str:
        from django.conf import settings
        dev_otp = getattr(settings, 'DEV_FIXED_OTP', None)
        if dev_otp:
            return str(dev_otp)
        return str(random.randint(100000, 999999))

    @classmethod
    def generate_and_send(cls, phone_number: str) -> str:
        """
        Creates or fetches user, invalidates old OTPs,
        generates new OTP, queues SMS task.
        Returns the OTP (for task to send via SMS).
        """
        user, _ = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'role': UserRole.CUSTOMER},
        )
        otp = cls.generate_otp()
        OTPToken.create_for_user(user, otp)

        from apps.auth_app.tasks import send_otp_sms
        send_otp_sms.delay(phone_number, otp)

        return otp

    @classmethod
    def verify(cls, phone_number: str, otp: str) -> User:
        """
        Verifies OTP for phone_number.
        Returns User on success, raises ValueError on failure.
        """
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            raise ValueError('User not found')

        token = (
            OTPToken.objects
            .filter(user=user, is_used=False)
            .order_by('-created_at')
            .first()
        )

        if token is None:
            raise ValueError('No active OTP found')

        if token.is_locked:
            raise ValueError('Too many attempts. Request a new OTP.')

        if token.is_expired:
            raise ValueError('OTP has expired')

        if not token.verify(otp):
            remaining = OTPToken.MAX_ATTEMPTS - token.attempts
            raise ValueError(f'Invalid OTP. {remaining} attempt(s) remaining.')

        return user


class JWTService:

    @staticmethod
    def issue_tokens(user: User) -> dict:
        """
        Returns access and refresh tokens with role and phone claims embedded.
        """
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['phone'] = user.phone_number

        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

    @staticmethod
    def update_location(user: User, latitude: float, longitude: float) -> User:
        user.registered_location = Point(longitude, latitude, srid=4326)
        user.save(update_fields=['registered_location', 'updated_at'])
        return user
