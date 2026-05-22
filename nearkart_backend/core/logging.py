"""
NearKart — Structured Logging

Two parallel streams on every event:
  1. logs/app.log          → JSON (Instagram-style, query with: jq 'select(.store_id=="X")')
  2. logs/<entity>.log     → Human-readable key=value per domain

Usage:
    from core.logging import log_event

    log_event('stores',       action='store_opened',         store_id='s1', user_id='u1')
    log_event('products',     action='product_wishlisted',   product_id='p1', user_id='u1')
    log_event('reservations', action='reservation_created',  reservation_id='r1',
              store_id='s1', product_id='p1', customer_id='u1', quantity=2)
    log_event('billing',      action='wallet_topup',         store_id='s1', amount='500.00')
    log_event('auth',         action='login_success',        user_id='u1', role='vendor')
    log_event('requests',     action='http_request',         method='GET', path='/api/v1/stores/')
"""
import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Single-line JSON for app.log — queryable with jq."""
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            'ts':     datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'level':  record.levelname,
            'logger': record.name,
        }
        if isinstance(record.msg, dict):
            payload.update(record.msg)
        else:
            payload['message'] = record.getMessage()
        if record.exc_info:
            payload['exc'] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class EntityFormatter(logging.Formatter):
    """Human-readable key=value lines for entity-specific log files."""
    def format(self, record: logging.LogRecord) -> str:
        ts    = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname.ljust(7)
        if isinstance(record.msg, dict):
            parts = '  '.join(f'{k}={v}' for k, v in record.msg.items())
            msg   = parts
        else:
            msg = record.getMessage()
        line = f'[{ts}] {level}  {msg}'
        if record.exc_info:
            line += '\n' + self.formatException(record.exc_info)
        return line


# ── Pre-wired entity loggers ─────────────────────────────────────────────────
_ENTITY_LOGGERS: dict[str, logging.Logger] = {
    'auth':         logging.getLogger('nearkart.auth'),
    'stores':       logging.getLogger('nearkart.stores'),
    'products':     logging.getLogger('nearkart.products'),
    'customers':    logging.getLogger('nearkart.customers'),
    'reservations': logging.getLogger('nearkart.reservations'),
    'videos':       logging.getLogger('nearkart.videos'),
    'billing':      logging.getLogger('nearkart.billing'),
    'requests':     logging.getLogger('nearkart.requests'),
}
_app_logger = logging.getLogger('nearkart.app')


def log_event(entity: str, level: str = 'info', **kwargs) -> None:
    """
    Write one structured event to both the entity log file and the global app.log.

    Args:
        entity : 'stores' | 'products' | 'customers' | 'reservations' |
                 'videos'  | 'billing'  | 'auth'      | 'requests'
        level  : 'debug' | 'info' | 'warning' | 'error'
        **kwargs: action (strongly recommended), plus any context fields:
                  store_id, user_id, product_id, reservation_id,
                  amount, plan, query, status, duration, etc.
    """
    payload: dict = {'entity': entity}
    payload.update({k: v for k, v in kwargs.items() if v not in (None, '', [])})

    entity_logger = _ENTITY_LOGGERS.get(entity)
    if entity_logger:
        getattr(entity_logger, level, entity_logger.info)(payload)

    getattr(_app_logger, level, _app_logger.info)(payload)
