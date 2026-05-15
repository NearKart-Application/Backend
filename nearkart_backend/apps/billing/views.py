"""
NearKart — Billing Views
GET  /api/v1/billing/plans/           → list all plans (public)
GET  /api/v1/billing/wallet/          → vendor wallet balance
POST /api/v1/billing/topup/           → add money to wallet
POST /api/v1/billing/subscribe/       → buy a plan
GET  /api/v1/billing/subscription/    → current subscription status
GET  /api/v1/billing/transactions/    → wallet transaction history
"""
import logging
from decimal import Decimal, InvalidOperation

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsVendor
from .models import Plan
from .serializers import PlanSerializer, SubscriptionSerializer, TransactionSerializer
from .services import BillingService

logger = logging.getLogger(__name__)
_TAG = 'Billing'


class PlanListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='List all available subscription plans (public)',
        responses={200: PlanSerializer(many=True)},
        auth=[],
    )
    def get(self, request):
        plans = Plan.objects.filter(is_active=True).order_by('price')
        return Response(PlanSerializer(plans, many=True).data)


class WalletView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Get current wallet balance (vendor only)',
        responses={200: OpenApiResponse(
            response=inline_serializer('WalletResponse', fields={
                'wallet_balance': s.DecimalField(max_digits=10, decimal_places=2),
                'store_name':     s.CharField(),
            })
        )},
    )
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response(
                {'error': 'not_found', 'message': 'You do not have a store yet.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        store = request.user.store
        return Response({
            'store_name':     store.name,
            'wallet_balance': str(store.wallet_balance),
        })


class TopupView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Add money to wallet (vendor only)',
        description=(
            'Credits the specified amount to the vendor\'s wallet instantly.\n\n'
            '**Dev mode:** No payment gateway — money is added immediately.\n\n'
            'In production this will be replaced with a Razorpay payment order flow.'
        ),
        request=inline_serializer('TopupRequest', fields={
            'amount': s.DecimalField(max_digits=10, decimal_places=2,
                                     help_text='Amount to add in ₹ (e.g. 500)'),
        }),
        responses={
            200: OpenApiResponse(
                response=inline_serializer('TopupResponse', fields={
                    'message':         s.CharField(),
                    'amount_added':    s.DecimalField(max_digits=10, decimal_places=2),
                    'wallet_balance':  s.DecimalField(max_digits=10, decimal_places=2),
                    'transaction_id':  s.UUIDField(),
                })
            ),
            400: OpenApiResponse(description='Invalid amount'),
        },
        examples=[
            OpenApiExample('Top up ₹500', request_only=True, value={'amount': '500.00'}),
            OpenApiExample('Top up ₹1000', request_only=True, value={'amount': '1000.00'}),
        ],
    )
    def post(self, request):
        if not hasattr(request.user, 'store'):
            return Response(
                {'error': 'not_found', 'message': 'You do not have a store yet.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            amount = Decimal(str(request.data.get('amount', '')))
            if amount <= 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            return Response(
                {'error': 'validation_error', 'message': 'amount must be a positive number.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        store = request.user.store
        txn = BillingService.topup(store, amount)
        return Response({
            'message':        f'₹{amount} added to wallet.',
            'amount_added':   str(amount),
            'wallet_balance': str(store.wallet_balance),
            'transaction_id': txn.id,
        })


class SubscribeView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Subscribe to a plan (vendor only)',
        description=(
            'Deducts the plan price from the vendor\'s wallet and activates the subscription.\n\n'
            '- Free plan costs ₹0 — no wallet balance needed\n'
            '- Basic plan costs ₹499 — must have ≥ ₹499 in wallet\n'
            '- Premium plan costs ₹999 — must have ≥ ₹999 in wallet\n\n'
            'Subscribing again (renew/upgrade) replaces the current subscription immediately.'
        ),
        request=inline_serializer('SubscribeRequest', fields={
            'plan_name': s.CharField(help_text='Plan slug: free | basic | premium'),
        }),
        responses={
            200: SubscriptionSerializer,
            400: OpenApiResponse(description='Insufficient balance or invalid plan'),
        },
        examples=[
            OpenApiExample('Subscribe Basic',   request_only=True, value={'plan_name': 'basic'}),
            OpenApiExample('Subscribe Premium', request_only=True, value={'plan_name': 'premium'}),
            OpenApiExample('Subscribe Free',    request_only=True, value={'plan_name': 'free'}),
        ],
    )
    def post(self, request):
        if not hasattr(request.user, 'store'):
            return Response(
                {'error': 'not_found', 'message': 'You do not have a store yet.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        plan_name = (request.data.get('plan_name') or '').strip().lower()
        try:
            plan = Plan.objects.get(name=plan_name, is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {'error': 'not_found',
                 'message': f'Plan "{plan_name}" not found. Valid plans: free, basic, premium.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        store = request.user.store
        try:
            sub = BillingService.subscribe(store, plan)
        except ValueError as e:
            return Response(
                {'error': 'insufficient_balance', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SubscriptionSerializer(sub).data)


class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Get current subscription status (vendor only)',
        responses={200: SubscriptionSerializer},
    )
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response(
                {'error': 'not_found', 'message': 'You do not have a store yet.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        sub = BillingService.get_subscription(request.user.store)
        if not sub:
            return Response(
                {'error': 'not_found', 'message': 'No subscription found. Subscribe to a plan first.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(SubscriptionSerializer(sub).data)


class TransactionListView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Wallet transaction history (vendor only)',
        responses={200: TransactionSerializer(many=True)},
    )
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response(
                {'error': 'not_found', 'message': 'You do not have a store yet.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        txns = BillingService.get_transactions(request.user.store)
        return Response(TransactionSerializer(txns, many=True).data)
