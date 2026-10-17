from rest_framework.permissions import BasePermission


class IsProductVendor(BasePermission):
    """Only Product Vendors (vendor_type=PRODUCT) can access inventory endpoints."""
    message = 'Inventory management is only available for product vendors.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == 'vendor'
            and hasattr(request.user, 'store')
            and request.user.store.vendor_type == 'product'
        )


class IsMasterAdmin(BasePermission):
    """Full platform access across all vendors and locations."""
    message = 'Master Admin access required.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == 'admin'
            and hasattr(request.user, 'admin_profile')
            and request.user.admin_profile.admin_level == 'master'
        )


class IsLocationAdmin(BasePermission):
    """Admin access scoped to their assigned district."""
    message = 'Admin access required.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == 'admin'
            and hasattr(request.user, 'admin_profile')
        )
