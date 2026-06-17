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
# All dev accounts use OTP 123456 (matches DEV_FIXED_OTP in .env)
_DEV_PHONE_OTPS = {
    '+919000000001': '123456',
    '+919000000002': '123456',
    '+919000000003': '123456',
    '+919000000006': '123456',
    '+919000000009': '123456',
    '+919000000010': '123456',
    '+919000000004': '123456',
    '+919000000005': '123456',
    '+919000000007': '123456',
    '+919000000008': '123456',
    '+919999999999': '123456',
    '+918888888888': '123456',
}


class OTPService:

    @staticmethod
    def generate_otp(phone_number: str = '') -> str:
        from django.conf import settings
        # In DEBUG any phone always gets 123456 — no real SMS needed for testing
        if getattr(settings, 'DEBUG', False):
            return '123456'
        dev_otp = getattr(settings, 'DEV_FIXED_OTP', None)
        if dev_otp:
            return str(dev_otp)
        return str(random.randint(100000, 999999))

    @classmethod
    def generate_and_send(cls, phone_number: str, delivery_method: str = 'sms') -> str:
        """
        Creates or fetches user, invalidates old OTPs,
        generates new OTP, queues SMS or voice task.
        Returns the OTP (for task to send).
        """
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            # New users start with no role — OtpScreen detects empty role and triggers role-select + location
            user = User.objects.create_user(phone_number=phone_number, role='')
        from django.conf import settings
        otp = cls.generate_otp(phone_number)
        OTPToken.create_for_user(user, otp)

        # Skip delivery entirely in DEBUG — 123456 works for any phone
        if not getattr(settings, 'DEBUG', False) and not getattr(settings, 'DEV_FIXED_OTP', None):
            if delivery_method == 'voice':
                from apps.auth_app.tasks import send_otp_voice
                send_otp_voice.delay(phone_number, otp)
            else:
                from apps.auth_app.tasks import send_otp_sms
                send_otp_sms.delay(phone_number, otp)

        return otp

    @classmethod
    def verify(cls, phone_number: str, otp: str) -> User:
        """
        Verifies OTP for phone_number.
        Returns User on success, raises ValueError on failure.
        """
        from django.conf import settings
        # Universal debug bypass — accepts 123456 for any phone without a real OTP token
        if getattr(settings, 'DEBUG', False) and otp == '123456':
            user, _ = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={'role': ''},
            )
            return user

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
