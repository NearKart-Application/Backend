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


# Keep in sync with DevTestUsers.kt in the mobile app
_DEV_PHONE_OTPS = {
    '+919000000001': '100001',
    '+919000000002': '200002',
    '+919000000003': '300003',
    '+919000000006': '600006',
    '+919000000009': '900009',
    '+919000000010': '100010',
    '+919000000004': '400004',
    '+919000000005': '500005',
    '+919000000007': '700007',
    '+919000000008': '800008',
    '+919999999999': '999999',
    '+918888888888': '888888',
}


class OTPService:

    @staticmethod
    def generate_otp(phone_number: str = '') -> str:
        from django.conf import settings
        if getattr(settings, 'DEBUG', False) and phone_number in _DEV_PHONE_OTPS:
            return _DEV_PHONE_OTPS[phone_number]
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
        from django.conf import settings
        otp = cls.generate_otp(phone_number)
        OTPToken.create_for_user(user, otp)

        is_dev_phone = getattr(settings, 'DEBUG', False) and phone_number in _DEV_PHONE_OTPS
        if not getattr(settings, 'DEV_FIXED_OTP', None) and not is_dev_phone:
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
