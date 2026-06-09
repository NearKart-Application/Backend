"""
NearKart — Billing Views
GET  /api/v1/billing/plans/                  → list all plans (public)
GET  /api/v1/billing/wallet/                 → vendor wallet balance
POST /api/v1/billing/topup/                  → admin top-up (dev/testing)
POST /api/v1/billing/subscribe/              → buy a plan (wallet must be funded)
GET  /api/v1/billing/subscription/           → current subscription status
GET  /api/v1/billing/transactions/           → wallet transaction history
POST /api/v1/billing/payment/initiate/       → create Razorpay order for a plan
POST /api/v1/billing/payment/verify/         → verify payment + fund wallet + subscribe
POST /api/v1/billing/payment/webhook/        → Razorpay webhook (payment.captured backup)
"""
import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.logging import log_event
from core.permissions import IsVendor
from .models import Coupon, Plan, Transaction
from .razorpay_service import RazorpayService
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
                {'error': 'no_store', 'message': 'You do not have a store yet.'},
                status=status.HTTP_400_BAD_REQUEST,
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
                {'error': 'no_store', 'message': 'You do not have a store yet.'},
                status=status.HTTP_400_BAD_REQUEST,
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
        log_event('billing', action='wallet_topup', store_id=str(store.id),
                  user_id=str(request.user.id), amount=str(amount),
                  new_balance=str(store.wallet_balance), transaction_id=str(txn.id))
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
                {'error': 'no_store', 'message': 'You do not have a store yet.'},
                status=status.HTTP_400_BAD_REQUEST,
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
        store       = request.user.store
        coupon_code = (request.data.get('coupon_code') or '').strip()
        coupon      = None
        if coupon_code:
            coupon, err = BillingService.validate_coupon(coupon_code, plan)
            if coupon is None:
                return Response({'error': 'invalid_coupon', 'message': err}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sub = BillingService.subscribe(store, plan, coupon=coupon)
        except ValueError as e:
            return Response(
                {'error': 'insufficient_balance', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        log_event('billing', action='plan_subscribed', store_id=str(store.id),
                  user_id=str(request.user.id), plan=plan_name,
                  price=str(plan.price), coupon=coupon_code or None,
                  expires_at=str(sub.expires_at))
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
                {'error': 'no_store', 'message': 'You do not have a store yet.'},
                status=status.HTTP_400_BAD_REQUEST,
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
                {'error': 'no_store', 'message': 'You do not have a store yet.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        txns = BillingService.get_transactions(request.user.store)
        return Response(TransactionSerializer(txns, many=True).data)


# ── Razorpay Payment Views ─────────────────────────────────────────────────────


class CouponValidateView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Validate a coupon code for a plan (vendor only)',
        request=inline_serializer('CouponValidateRequest', fields={
            'code':      s.CharField(help_text='Coupon code'),
            'plan_name': s.CharField(help_text='Plan slug: basic | premium'),
        }),
        responses={
            200: OpenApiResponse(
                response=inline_serializer('CouponValidateResponse', fields={
                    'valid':            s.BooleanField(),
                    'discount_percent': s.IntegerField(),
                    'final_price':      s.CharField(),
                    'message':          s.CharField(),
                })
            ),
        },
    )
    def post(self, request):
        code      = (request.data.get('code') or '').strip()
        plan_name = (request.data.get('plan_name') or '').strip().lower()

        if not code or not plan_name:
            return Response({'error': 'validation_error', 'message': 'code and plan_name are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan = Plan.objects.get(name=plan_name, is_active=True)
        except Plan.DoesNotExist:
            return Response({'error': 'not_found', 'message': f'Plan "{plan_name}" not found.'}, status=status.HTTP_404_NOT_FOUND)

        coupon, err = BillingService.validate_coupon(code, plan)
        if coupon is None:
            return Response({'valid': False, 'discount_percent': 0, 'final_price': str(plan.price), 'message': err})

        final_price = BillingService.apply_discount(plan.price, coupon)
        return Response({
            'valid':            True,
            'discount_percent': coupon.discount_percent,
            'final_price':      str(final_price),
            'message':          f'{coupon.discount_percent}% off applied!' + (' Subscription is free!' if final_price == 0 else ''),
        })


class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Initiate Razorpay payment for a plan (vendor only)',
        description=(
            'Creates a Razorpay order for the selected plan price.\n\n'
            'If a coupon_code is provided and reduces price to 0, returns a direct subscription '
            'instead of a Razorpay order (field `coupon_free: true`).\n\n'
            '**Dev mode:** returns a mock order — no real payment processed.'
        ),
        request=inline_serializer('PaymentInitiateRequest', fields={
            'plan_name':   s.CharField(help_text='Plan slug: basic | premium'),
            'coupon_code': s.CharField(required=False, help_text='Optional coupon code'),
        }),
        responses={
            200: OpenApiResponse(
                response=inline_serializer('PaymentInitiateResponse', fields={
                    'order_id':        s.CharField(),
                    'amount':          s.IntegerField(help_text='Amount in paise (₹×100)'),
                    'currency':        s.CharField(),
                    'plan_name':       s.CharField(),
                    'receipt':         s.CharField(),
                    'razorpay_key_id': s.CharField(),
                    'coupon_free':     s.BooleanField(help_text='True if coupon made it free — no Razorpay needed'),
                })
            ),
            400: OpenApiResponse(description='Invalid plan or coupon'),
        },
        examples=[
            OpenApiExample('Initiate Basic',   request_only=True, value={'plan_name': 'basic'}),
            OpenApiExample('Initiate Premium', request_only=True, value={'plan_name': 'premium'}),
            OpenApiExample('Coupon free',      request_only=True, value={'plan_name': 'basic', 'coupon_code': 'NEARSPOT100'}),
        ],
    )
    def post(self, request):
        if not hasattr(request.user, 'store'):
            return Response(
                {'error': 'no_store', 'message': 'You do not have a store yet.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan_name   = (request.data.get('plan_name')   or '').strip().lower()
        coupon_code = (request.data.get('coupon_code') or '').strip()

        try:
            plan = Plan.objects.get(name=plan_name, is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': f'Plan "{plan_name}" not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        coupon = None
        if coupon_code:
            coupon, err = BillingService.validate_coupon(coupon_code, plan)
            if coupon is None:
                return Response({'error': 'invalid_coupon', 'message': err}, status=status.HTTP_400_BAD_REQUEST)

        final_price = BillingService.apply_discount(plan.price, coupon)

        # Coupon makes it free — subscribe directly, no Razorpay needed
        if final_price == 0:
            store = request.user.store
            sub   = BillingService.subscribe(store, plan, coupon=coupon)
            return Response({
                'coupon_free':  True,
                'plan_name':    plan_name,
                'subscription': SubscriptionSerializer(sub).data,
            })

        store   = request.user.store
        receipt = f'store_{str(store.id)[:8]}_{plan_name}_{int(timezone.now().timestamp())}'
        order   = RazorpayService.create_order(
            amount_inr=final_price,
            receipt=receipt,
            notes={'store_id': str(store.id), 'plan': plan_name},
        )
        return Response({
            'coupon_free':     False,
            'order_id':        order['id'],
            'amount':          order['amount'],
            'currency':        order['currency'],
            'plan_name':       plan_name,
            'receipt':         receipt,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        })


class PaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Verify Razorpay payment and activate subscription (vendor only)',
        description=(
            'After the Razorpay checkout SDK succeeds, send the three IDs here to verify '
            'the HMAC-SHA256 signature. On success the plan price is credited to the wallet '
            'and the subscription is activated immediately.\n\n'
            '**Dev mode:** signature check is skipped — any values work.'
        ),
        request=inline_serializer('PaymentVerifyRequest', fields={
            'razorpay_order_id':   s.CharField(),
            'razorpay_payment_id': s.CharField(),
            'razorpay_signature':  s.CharField(),
            'plan_name':           s.CharField(help_text='Must match the plan from initiate step'),
        }),
        responses={
            200: SubscriptionSerializer,
            400: OpenApiResponse(description='Signature mismatch or invalid plan'),
        },
        examples=[
            OpenApiExample(
                'Verify payment (dev)',
                request_only=True,
                value={
                    'razorpay_order_id':   'order_DEV_store_abc',
                    'razorpay_payment_id': 'pay_DEV_12345',
                    'razorpay_signature':  'mock_signature',
                    'plan_name':           'basic',
                },
            ),
        ],
    )
    def post(self, request):
        if not hasattr(request.user, 'store'):
            return Response(
                {'error': 'no_store', 'message': 'You do not have a store yet.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_id   = (request.data.get('razorpay_order_id')   or '').strip()
        payment_id = (request.data.get('razorpay_payment_id') or '').strip()
        signature  = (request.data.get('razorpay_signature')  or '').strip()
        plan_name  = (request.data.get('plan_name')           or '').strip().lower()

        if not all([order_id, payment_id, signature, plan_name]):
            return Response(
                {'error': 'validation_error', 'message': 'razorpay_order_id, razorpay_payment_id, razorpay_signature and plan_name are all required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not RazorpayService.verify_payment_signature(order_id, payment_id, signature):
            return Response(
                {'error': 'payment_failed', 'message': 'Payment signature verification failed. Do not retry — contact support.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            plan = Plan.objects.get(name=plan_name, is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': f'Plan "{plan_name}" not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        store = request.user.store
        # Credit wallet then subscribe (topup creates the transaction record with Razorpay payment_id)
        BillingService.topup(store, plan.price, reference_id=payment_id)
        store.refresh_from_db(fields=['wallet_balance'])
        try:
            sub = BillingService.subscribe(store, plan)
        except ValueError as e:
            return Response(
                {'error': 'subscription_failed', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info('Payment verified: store=%s plan=%s payment_id=%s', store.id, plan_name, payment_id)
        return Response(SubscriptionSerializer(sub).data)


class PaymentWebhookView(APIView):
    """
    Razorpay webhook endpoint — backup for payment.captured events.
    Registers with Razorpay dashboard: POST /api/v1/billing/payment/webhook/
    No JWT auth — authenticated via X-Razorpay-Signature header.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # skip JWT for webhook

    @extend_schema(
        tags=[_TAG],
        summary='Razorpay webhook receiver (no auth — verified by signature)',
        description=(
            'Razorpay calls this endpoint after a payment event. '
            'Verifies the `X-Razorpay-Signature` header before processing.\n\n'
            'Handles: `payment.captured` — credits wallet and activates subscription if not already done.\n\n'
            '**Register this URL in Razorpay Dashboard → Webhooks.**'
        ),
        request=inline_serializer('WebhookPayload', fields={
            'event':   s.CharField(),
            'payload': s.DictField(),
        }),
        responses={
            200: OpenApiResponse(description='Webhook processed'),
            400: OpenApiResponse(description='Signature invalid or missing'),
        },
        auth=[],
    )
    def post(self, request):
        signature = request.headers.get('X-Razorpay-Signature', '')
        body = request.body

        if not RazorpayService.verify_webhook_signature(body, signature):
            logger.warning('Razorpay webhook signature mismatch')
            return Response({'error': 'invalid_signature'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response({'error': 'invalid_payload'}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get('event')
        logger.info('Razorpay webhook received: event=%s', event)

        if event == 'payment.captured':
            payment = payload.get('payload', {}).get('payment', {}).get('entity', {})
            payment_id = payment.get('id', '')
            order_id   = payment.get('order_id', '')
            notes      = payment.get('notes', {})
            store_id   = notes.get('store_id', '')
            plan_name  = notes.get('plan', '')

            # Skip if already processed (idempotency: check for existing topup transaction)
            if payment_id and Transaction.objects.filter(reference_id=payment_id).exists():
                logger.info('Razorpay webhook: payment %s already processed, skipping', payment_id)
                return Response({'status': 'already_processed'})

            if store_id and plan_name:
                try:
                    from apps.stores.models import Store
                    store = Store.objects.get(id=store_id)
                    plan  = Plan.objects.get(name=plan_name, is_active=True)
                    BillingService.topup(store, plan.price, reference_id=payment_id)
                    store.refresh_from_db(fields=['wallet_balance'])
                    BillingService.subscribe(store, plan)
                    logger.info('Razorpay webhook: activated %s for store %s', plan_name, store_id)
                except Exception as exc:
                    logger.exception('Razorpay webhook: failed to activate plan — %s', exc)
                    return Response({'error': 'processing_failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'status': 'ok'})
