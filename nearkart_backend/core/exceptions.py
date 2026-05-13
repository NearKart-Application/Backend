"""
NearKart — Custom Exception Handler
Consistent error response format for all API errors
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Returns consistent error format:
    {
        "error": "error_type",
        "message": "Human readable message",
        "code": "ERROR_CODE",
        "details": {...}
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_map = {
            400: 'validation_error',
            401: 'authentication_failed',
            403: 'permission_denied',
            404: 'not_found',
            405: 'method_not_allowed',
            429: 'throttled',
            500: 'server_error',
        }

        error_type = error_map.get(response.status_code, 'error')
        message = _extract_message(response.data)
        code = _extract_code(response.data)
        details = _extract_details(response.data)

        response.data = {
            'error': error_type,
            'message': message,
            'code': code,
            'details': details,
        }

    return response


def _extract_message(data):
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        if 'message' in data:
            return str(data['message'])
        # Return first field error as message
        for key, value in data.items():
            if isinstance(value, list) and value:
                return str(value[0])
    if isinstance(data, list) and data:
        return str(data[0])
    return 'An error occurred'


def _extract_code(data):
    if isinstance(data, dict):
        if 'code' in data:
            return str(data['code']).upper()
        if 'detail' in data and hasattr(data['detail'], 'code'):
            return str(data['detail'].code).upper()
    return 'ERROR'


def _extract_details(data):
    if isinstance(data, dict):
        # Remove keys already extracted
        return {
            k: v for k, v in data.items()
            if k not in ('detail', 'message', 'code')
        }
    return {}
