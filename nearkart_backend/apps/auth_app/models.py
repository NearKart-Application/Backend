"""
NearKart — Auth Models
User, OTPToken, DeviceToken
"""
import functools
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
            for attempt in range(100):
                pid = _generate_profile_id(name=name, role=role)
                if not self.model.objects.filter(profile_id=pid).exists():
                    extra_fields['profile_id'] = pid
                    break
            else:
                raise RuntimeError('Could not generate unique profile_id after 100 attempts')
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
    avatar       = models.URLField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.CharField(max_length=500, blank=True, default='')
    admin_assigned_city = models.CharField(max_length=500, blank=True, default='')
    location_city       = models.CharField(max_length=150, blank=True, default='')
    location_district   = models.CharField(max_length=150, blank=True, default='')
    location_state      = models.CharField(max_length=150, blank=True, default='')
    registered_location = gis_models.PointField(
        srid=4326, null=True, blank=True, spatial_index=True
    )

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = UserManager()

    @functools.cached_property
    def store(self):
        """
        Returns the vendor's primary (first active) store.
        Raises AttributeError when the user has no active store so that
        existing hasattr(user, 'store') guard patterns continue to work.
        Cached per instance to avoid repeated DB hits within a single request.
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


class CustomerActivityLog(BaseModel):
    """Tracks meaningful customer interactions: views, searches, wishlist, reservations."""

    class Action(models.TextChoices):
        PRODUCT_VIEW       = 'product_view',       'Product Viewed'
        STORE_VIEW         = 'store_view',          'Store Viewed'
        SEARCH             = 'search',              'Search'
        WISHLIST_ADD       = 'wishlist_add',        'Wishlisted'
        WISHLIST_REMOVE    = 'wishlist_remove',     'Unwishlisted'
        RESERVATION_CREATE = 'reservation_create',  'Reservation Made'

    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='activity_logs')
    phone       = models.CharField(max_length=20, blank=True, db_index=True)
    action      = models.CharField(max_length=25, choices=Action.choices, db_index=True)
    entity_type = models.CharField(max_length=20, blank=True)   # product / store / query
    entity_id   = models.CharField(max_length=40, blank=True, db_index=True)
    entity_name = models.CharField(max_length=250, blank=True)
    meta        = models.JSONField(default=dict, blank=True)     # query text, results count, etc.
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    city        = models.CharField(max_length=150, blank=True)
    device_type = models.CharField(max_length=10, blank=True)   # mobile / tablet / desktop

    class Meta:
        db_table = 'customer_activity_logs'
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['user', 'created_at'],   name='cal_user_idx'),
            models.Index(fields=['action', 'created_at'], name='cal_action_idx'),
        ]

    def __str__(self):
        return f'{self.phone or self.user_id} [{self.action}] @ {self.created_at}'


class UserLoginLog(BaseModel):
    """Audit trail for every login attempt — success and failure."""
    DEVICE_TYPES = [('mobile', 'Mobile'), ('tablet', 'Tablet'), ('desktop', 'Desktop'), ('unknown', 'Unknown')]

    user           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='login_logs')
    phone          = models.CharField(max_length=20, db_index=True)
    role           = models.CharField(max_length=20, blank=True)
    success        = models.BooleanField(default=True, db_index=True)
    failure_reason = models.CharField(max_length=50, blank=True)

    # Network
    ip_address     = models.GenericIPAddressField(null=True, blank=True)
    city           = models.CharField(max_length=150, blank=True)

    # Device (parsed from User-Agent or sent by mobile app)
    device_type    = models.CharField(max_length=10, choices=DEVICE_TYPES, default='unknown')
    device_name    = models.CharField(max_length=200, blank=True)   # e.g. "Samsung SM-G991B"
    os             = models.CharField(max_length=50, blank=True)    # Android / iOS / Windows / macOS
    os_version     = models.CharField(max_length=30, blank=True)
    browser        = models.CharField(max_length=100, blank=True)   # Chrome / Safari / NearKart App
    app_version    = models.CharField(max_length=30, blank=True)    # mobile app version
    user_agent     = models.TextField(blank=True)

    class Meta:
        db_table = 'auth_login_logs'
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['phone', 'created_at'],  name='login_log_phone_idx'),
            models.Index(fields=['success', 'created_at'], name='login_log_success_idx'),
        ]

    def __str__(self):
        status = 'OK' if self.success else f'FAIL({self.failure_reason})'
        return f'{self.phone} [{status}] @ {self.created_at}'


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


class SocialAccount(BaseModel):
    """Stores the link between a NearSpot user and a third-party OAuth provider."""
    PROVIDER_GOOGLE = 'google'
    PROVIDER_APPLE  = 'apple'
    PROVIDER_CHOICES = [('google', 'Google'), ('apple', 'Apple')]

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider     = models.CharField(max_length=20, choices=PROVIDER_CHOICES, db_index=True)
    provider_uid = models.CharField(max_length=255, db_index=True)
    extra_data   = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'auth_social_accounts'
        unique_together = [('provider', 'provider_uid')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.phone_number} [{self.provider}]'
