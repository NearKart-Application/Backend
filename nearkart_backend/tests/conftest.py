"""
NearKart — Shared Test Fixtures
Provides reusable users, tokens, stores, and plans for all test modules.
"""
import pytest
from decimal import Decimal
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from django.utils import timezone
from datetime import timedelta
from apps.auth_app.models import User, UserRole
from apps.stores.models import Store
from apps.billing.models import Plan, Subscription


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_token(user):
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    return str(refresh.access_token)


def auth_client(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {make_token(user)}')
    return client


# ── Users ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def customer(db):
    return User.objects.create_user(phone_number='+919000000001', role=UserRole.CUSTOMER)


@pytest.fixture
def customer2(db):
    return User.objects.create_user(phone_number='+919000000002', role=UserRole.CUSTOMER)


@pytest.fixture
def vendor_user(db):
    return User.objects.create_user(phone_number='+919000000010', role=UserRole.VENDOR)


@pytest.fixture
def vendor_user2(db):
    return User.objects.create_user(phone_number='+919000000011', role=UserRole.VENDOR)


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(phone_number='+919000000099', role=UserRole.ADMIN, is_staff=True)


@pytest.fixture
def master_admin_user(db):
    return User.objects.create_user(phone_number='+919000000098', role='master_admin', is_staff=True)


# ── API Clients ───────────────────────────────────────────────────────────────

@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def customer_client(customer):
    return auth_client(customer)


@pytest.fixture
def customer2_client(customer2):
    return auth_client(customer2)


@pytest.fixture
def vendor_client(vendor_user):
    return auth_client(vendor_user)


@pytest.fixture
def vendor2_client(vendor_user2):
    return auth_client(vendor_user2)


@pytest.fixture
def admin_client(admin_user):
    return auth_client(admin_user)


@pytest.fixture
def master_admin_client(master_admin_user):
    return auth_client(master_admin_user)


# ── Store ─────────────────────────────────────────────────────────────────────

def _attach_subscription(store):
    plan, _ = Plan.objects.get_or_create(
        name='test_plan',
        defaults={
            'display_name': 'Test Plan',
            'price': Decimal('0.00'),
            'duration_days': 365,
            'video_limit': 0,
            'product_limit': 0,
            'is_active': True,
        },
    )
    Subscription.objects.get_or_create(
        store=store,
        defaults={
            'plan': plan,
            'started_at': timezone.now(),
            'expires_at': timezone.now() + timedelta(days=365),
            'is_active': True,
        },
    )
    return store


@pytest.fixture
def store(db, vendor_user):
    s = Store.objects.create(
        owner=vendor_user,
        name='Test Store',
        description='A test store',
        category='fashion',
        address='123 Test Street, Chennai',
        locality='Anna Nagar',
        location=Point(80.2707, 13.0827, srid=4326),
        is_active=True,
        is_verified=True,
    )
    return _attach_subscription(s)


@pytest.fixture
def store2(db, vendor_user2):
    s = Store.objects.create(
        owner=vendor_user2,
        name='Second Store',
        description='Another test store',
        category='food',
        address='456 Other Street, Chennai',
        locality='T Nagar',
        location=Point(80.2500, 13.0600, srid=4326),
        is_active=True,
        is_verified=True,
    )
    return _attach_subscription(s)


# ── Plans ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def plan_basic(db):
    return Plan.objects.create(
        name='basic', display_name='Basic Plan',
        price=Decimal('299.00'), duration_days=30,
        video_limit=20, product_limit=0, is_active=True,
    )


@pytest.fixture
def plan_premium(db):
    return Plan.objects.create(
        name='premium', display_name='Premium Plan',
        price=Decimal('499.00'), duration_days=30,
        video_limit=0, product_limit=0, is_active=True,
    )


@pytest.fixture
def all_plans(plan_basic, plan_premium):
    return [plan_basic, plan_premium]
