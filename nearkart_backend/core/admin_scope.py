"""
Geographic scope helpers for the Django admin.

Every admin class that shows location-scoped data (Stores, Users, etc.)
calls get_store_scope(request) or get_user_scope(request) inside
get_queryset() so that a State/District/City/Area admin only sees
records within their assigned area.

Master admins get an empty dict → no filter → see everything.
"""


def _get_profile(request):
    try:
        return request.user.admin_profile
    except Exception:
        return None


def get_store_scope(request):
    """
    Returns filter kwargs to restrict a Store queryset to the
    logged-in admin's assigned area. Empty dict = no restriction.
    """
    profile = _get_profile(request)
    if profile is None or profile.is_master:
        return {}
    return profile.scope_filter_for_stores


def get_user_scope(request):
    """
    Returns filter kwargs to restrict a User queryset to the
    logged-in admin's assigned area. Empty dict = no restriction.
    """
    profile = _get_profile(request)
    if profile is None or profile.is_master:
        return {}
    return profile.scope_filter_for_users


def scope_label(request):
    """
    Returns a human-readable string describing the admin's current scope.
    Used in admin headings / messages.
    e.g. "Andhra Pradesh › Visakhapatnam"
    """
    profile = _get_profile(request)
    if profile is None or profile.is_master:
        return 'All India'
    parts = filter(None, [
        profile.assigned_state,
        profile.assigned_district,
        profile.assigned_city,
        profile.assigned_area,
    ])
    return ' › '.join(parts) or 'All India'
