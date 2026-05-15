"""
NearKart — Blacklist Views
POST /api/v1/stores/<store_id>/blacklist/<customer_id>/   → toggle block/unblock
GET  /api/v1/stores/<store_id>/blacklist/                 → list blocked customers
"""
import logging

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth_app.models import User
from apps.stores.models import Store
from core.permissions import IsVendor
from .serializers import BlacklistSerializer
from .services import BlacklistService

logger = logging.getLogger(__name__)
_TAG = 'Blacklist'


class BlacklistToggleView(APIView):
    """POST /stores/<store_id>/blacklist/<customer_id>/ — block or unblock a customer."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Block / unblock a customer (vendor only)',
        description=(
            'Toggles a customer\'s blacklist status for the vendor\'s store.\n\n'
            '- First call → **blocks** the customer (`is_blocked: true`)\n'
            '- Second call → **unblocks** (`is_blocked: false`)\n\n'
            'A blocked customer **cannot**:\n'
            '- Follow or review this store\n'
            '- Start a new chat conversation with this store\n'
            '- Connect via WebSocket to existing conversations with this store'
        ),
        request=inline_serializer('BlacklistToggleRequest', fields={
            'reason': s.CharField(required=False, allow_blank=True,
                                  help_text='Optional reason for blocking'),
        }),
        responses={
            200: OpenApiResponse(
                response=inline_serializer('BlacklistToggleResponse', fields={
                    'is_blocked': s.BooleanField(),
                    'message':    s.CharField(),
                }),
            ),
            403: OpenApiResponse(description='Not the store owner'),
            404: OpenApiResponse(description='Store or customer not found'),
        },
        examples=[
            OpenApiExample('Block with reason', request_only=True,
                           value={'reason': 'Spamming and abusive messages'}),
            OpenApiExample('Block no reason', request_only=True,
                           value={}),
        ],
    )
    def post(self, request, store_id, customer_id):
        store = self._get_owned_store(store_id, request.user)
        if isinstance(store, Response):
            return store

        try:
            customer = User.objects.get(id=customer_id, role='customer')
        except User.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Customer not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        reason = (request.data.get('reason') or '').strip()
        is_blocked, _ = BlacklistService.toggle(store, customer, reason=reason)
        msg = f'Customer blocked.' if is_blocked else 'Customer unblocked.'
        return Response({'is_blocked': is_blocked, 'message': msg})

    def _get_owned_store(self, store_id, user):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Store not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if store.owner_id != user.id:
            return Response(
                {'error': 'permission_denied', 'message': 'You do not own this store.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return store


class BlacklistListView(APIView):
    """GET /stores/<store_id>/blacklist/ — list all customers blocked by this store."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='List blocked customers for a store (vendor only)',
        responses={200: BlacklistSerializer(many=True)},
    )
    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Store not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if store.owner_id != request.user.id:
            return Response(
                {'error': 'permission_denied', 'message': 'You do not own this store.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = BlacklistService.list_for_store(store)
        return Response(BlacklistSerializer(qs, many=True).data)
