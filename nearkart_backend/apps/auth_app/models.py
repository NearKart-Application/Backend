"""
NearKart — Auth Models
User, OTPToken, DeviceToken
"""
import hashlib
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone
from datetime import timedelta


def _generate_profile_id(name: str = '', area: str = '', role: str = '') -> str:
    from core.utils.codes import make_ns_code
    return make_ns_code(name=name, area=area, role=role)

from core.models import BaseModel


class UserRole(models.TextChoices):
    CUSTOMER     = 'customer',     'Customer'
    VENDOR       = 'vendor',       'Vendor'
    ADMIN        = 'admin',        'Admin'
    MASTER_ADMIN = 'master_admin', 'Master Admin'


class UserManager(BaseUserManager):
    def create_user(self, phone_number, role=UserRole.CUSTOMER, **extra_fields):
        if not phone_number:
            raise ValueError('Phone number is required')
        if not extra_fields.get('profile_id'):
            name = extra_fields.get('full_name', '')
            while True:
                pid = _generate_profile_id(name=name, role=role)
                if not self.model.objects.filter(profile_id=pid).exists():
                    extra_fields['profile_id'] = pid
                    break
        user = self.model(phone_number=phone_number, role=role, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, **extra_fields):
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    phone_number = models.CharField(max_length=15, unique=True, db_index=True)
    profile_id   = models.CharField(max_length=16, unique=True, db_index=True, blank=True, default='')
    role         = models.CharField(max_length=12, choices=UserRole.choices, default='', blank=True)
    full_name    = models.CharField(max_length=150, blank=True)
    email        = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.CharField(max_length=500, blank=True, default='')
    admin_assigned_city = models.CharField(max_length=100, blank=True, default='')
    registered_location = gis_models.PointField(
        srid=4326, null=True, blank=True, spatial_index=True
    )

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def store(self):
        """
        Returns the vendor's primary (first active) store.
        Raises AttributeError when the user has no active store so that
        existing hasattr(user, 'store') guard patterns continue to work.
        """
        s = self.stores.filter(is_active=True).order_by('created_at').first()
        if s is None:
            raise AttributeError('User has no active store')
        return s

    class Meta:
        db_table = 'auth_users'
        ordering = ['-created_at']

    def __str__(self):
        return self.phone_number


class OTPToken(BaseModel):
    MAX_ATTEMPTS = 5
    OTP_EXPIRY_MINUTES = 5

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_tokens')
    otp_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'auth_otp_tokens'
        ordering = ['-created_at']

    @classmethod
    def make_hash(cls, otp: str) -> str:
        return hashlib.sha256(otp.encode()).hexdigest()

    @classmethod
    def create_for_user(cls, user: User, otp: str) -> 'OTPToken':
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        return cls.objects.create(
            user=user,
            otp_hash=cls.make_hash(otp),
            expires_at=timezone.now() + timedelta(minutes=cls.OTP_EXPIRY_MINUTES),
        )

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_locked(self) -> bool:
        return self.attempts >= self.MAX_ATTEMPTS

    def verify(self, otp: str) -> bool:
        if self.is_used or self.is_expired or self.is_locked:
            return False
        self.attempts += 1
        if self.otp_hash == self.make_hash(otp):
            self.is_used = True
            self.save(update_fields=['is_used', 'attempts'])
            return True
        self.save(update_fields=['attempts'])
        return False


class DeviceToken(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    fcm_token = models.CharField(max_length=512)
    device_type = models.CharField(
        max_length=10,
        choices=[('android', 'Android'), ('ios', 'iOS')],
        default='android',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'auth_device_tokens'
        unique_together = [('user', 'fcm_token')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.phone_number} - {self.device_type}'
