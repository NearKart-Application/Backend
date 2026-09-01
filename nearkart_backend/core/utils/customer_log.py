"""
Lightweight helper to write a CustomerActivityLog row without crashing the caller.
Only logs authenticated users — avoids flooding from crawlers and anonymous traffic.
Import: from core.utils.customer_log import log_customer_action
"""
from core.utils.ua_parser import get_client_ip, parse_ua


def log_customer_action(
    request,
    action: str,
    *,
    entity_type: str = '',
    entity_id: str = '',
    entity_name: str = '',
    meta: dict | None = None,
) -> None:
    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return  # skip anonymous — too much noise
    if user.role not in ('customer', ''):
        return  # only track customer actions here; vendors have VendorActionLog
    try:
        from apps.auth_app.models import CustomerActivityLog
        ua = request.META.get('HTTP_USER_AGENT', '')
        device_type = parse_ua(ua)['device_type']
        CustomerActivityLog.objects.create(
            user=user,
            phone=str(user.phone_number),
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else '',
            entity_name=entity_name or '',
            meta=meta or {},
            ip_address=get_client_ip(request) or None,
            city=getattr(user, 'location_city', ''),
            device_type=device_type,
        )
    except Exception:
        pass
