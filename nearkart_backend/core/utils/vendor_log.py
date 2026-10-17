"""
Lightweight helper to write a VendorActionLog row without crashing the calling view.
Import: from core.utils.vendor_log import log_vendor_action
"""
from core.utils.ua_parser import get_client_ip


def log_vendor_action(
    request,
    action: str,
    *,
    store=None,
    entity_type: str = '',
    entity_id: str = '',
    entity_name: str = '',
    meta: dict | None = None,
) -> None:
    try:
        from apps.stores.models import VendorActionLog
        VendorActionLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            store=store or (request.user.store if hasattr(request.user, 'store') else None),
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else '',
            entity_name=entity_name or '',
            meta=meta or {},
            ip_address=get_client_ip(request) or None,
        )
    except Exception:
        pass  # logging must never break the calling view
