from django.urls import path
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


def health_check(request):
    # Check DB
    try:
        connection.ensure_connection()
        db_status = 'ok'
    except Exception:
        db_status = 'error'

    # Check Redis
    try:
        cache.set('health_check', '1', 5)
        redis_status = 'ok' if cache.get('health_check') else 'error'
    except Exception:
        redis_status = 'error'

    status_code = 200 if db_status == 'ok' and redis_status == 'ok' else 503
    return JsonResponse({
        'status': 'ok' if status_code == 200 else 'degraded',
        'db': db_status,
        'redis': redis_status,
        'version': '1.0.0',
        'environment': 'development',
    }, status=status_code)


urlpatterns = [path('', health_check)]
