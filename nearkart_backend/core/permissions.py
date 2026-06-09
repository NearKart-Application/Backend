"""
NearKart — Custom DRF Permissions
"""
from rest_framework.permissions import BasePermission


class IsCustomer(BasePermission):
    """User must be authenticated with role=customer."""
    message = 'Customer access only.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'customer'
        )


class IsVendor(BasePermission):
    """User must be authenticated with role=vendor."""
    message = 'Vendor access only.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'vendor'
        )


class IsAdmin(BasePermission):
    """User must be authenticated with role=admin or master_admin."""
    message = 'Admin access only.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ('admin', 'master_admin')
        )


class IsMasterAdmin(BasePermission):
    """User must be authenticated with role=master_admin."""
    message = 'Master admin access only.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'master_admin'
        )


class IsVendorOrAdmin(BasePermission):
    """User must be vendor or admin."""
    message = 'Vendor or admin access only.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ('vendor', 'admin')
        )


class IsStoreOwner(BasePermission):
    """
    Object-level permission — vendor can only access their own store.
    Used on store, product, video, invoice endpoints.
    """
    message = 'You do not have permission to access this store.'

    def has_object_permission(self, request, view, obj):
        # obj can be Store, Product, Video, Invoice etc.
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'store'):
            return obj.store.owner == request.user
        return False


class IsVendorSubscribed(BasePermission):
    """Vendor must have an active (non-expired) subscription."""
    message = 'An active subscription is required. Please subscribe to a plan in Billing & Plans.'

    def has_permission(self, request, view):
        from django.utils import timezone
        if not (request.user and request.user.is_authenticated and request.user.role == 'vendor'):
            return False
        if not hasattr(request.user, 'store'):
            return False
        try:
            sub = request.user.store.subscription
            return sub.is_active and sub.expires_at > timezone.now()
        except Exception:
            return False
