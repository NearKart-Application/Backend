"""
NearKart — Loyalty Views

GET  /loyalty/           → balance + referral code
GET  /loyalty/history/   → transaction list
POST /loyalty/apply-referral/ → apply someone's referral code (one-time)
POST /loyalty/redeem/    → redeem points (returns discount in rupees)

GET  /wallet/requests/   → list user's withdrawal requests
POST /wallet/requests/   → submit a new withdrawal request
POST /wallet/topup/initiate/ → initiate Razorpay order for wallet top-up
POST /wallet/topup/verify/   → verify Razorpay payment and credit points
"""
import hashlib
import hmac
import logging

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.pagination import StandardOffsetPagination
from drf_spectacular.utils import extend_schema, inline_serializer
from drf_spectacular.types import OpenApiTypes

from rest_framework import serializers as s
from rest_framework import status as drf_status

from .models import LoyaltyTransaction, WalletWithdrawalRequest
from .serializers import (
    LoyaltyBalanceSerializer,
    LoyaltyTransactionSerializer,
    ApplyReferralSerializer,
    RedeemPointsSerializer,
    WalletWithdrawalRequestSerializer,
)
from .services import LoyaltyService, POINTS_PER_RUPEE

logger = logging.getLogger(__name__)
_TAG = 'Loyalty'


class LoyaltyBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Get loyalty balance & referral code',
        description='Returns current points balance, total earned/redeemed, and unique referral code.',
        responses={200: LoyaltyBalanceSerializer},
    )
    def get(self, request):
        account = LoyaltyService.get_account(request.user)
        return Response(LoyaltyBalanceSerializer(account).data)


class LoyaltyHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Loyalty transaction history',
        description='Returns earn and redeem history, newest first.',
        responses={200: LoyaltyTransactionSerializer(many=True)},
    )
    def get(self, request):
        account = LoyaltyService.get_account(request.user)
        txns = LoyaltyTransaction.objects.filter(account=account).order_by('-created_at')
        paginator = StandardOffsetPagination()
        page = paginator.paginate_queryset(txns, request)
        return paginator.get_paginated_response(LoyaltyTransactionSerializer(page, many=True).data)


class ApplyReferralView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Apply a referral code',
        description='One-time action. Awards loyalty points to the referrer. Each user can only apply one referral code.',
        request=ApplyReferralSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        ser = ApplyReferralSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        try:
            result = LoyaltyService.apply_referral(request.user, ser.validated_data['referral_code'])
        except ValueError as e:
            return Response({'error': 'invalid_referral', 'message': str(e)}, status=400)

        return Response({
            'message': f'Referral applied! Your friend earned {result["points_awarded"]} loyalty points.',
            'points_awarded': result['points_awarded'],
        })


class RedeemPointsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Redeem loyalty points',
        description=(
            'Deducts points from the user balance and returns the equivalent rupee discount. '
            '10 points = ₹1. Min: 50 pts. Max: 500 pts per transaction. '
            'Typically called from the reservation flow before confirming a hold.'
        ),
        request=RedeemPointsSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        ser = RedeemPointsSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        try:
            discount_rupees = LoyaltyService.redeem_points(
                user=request.user,
                points=ser.validated_data['points'],
                description=ser.validated_data.get('description', 'Points redeemed'),
            )
        except ValueError as e:
            return Response({'error': 'redemption_failed', 'message': str(e)}, status=400)

        account = LoyaltyService.get_account(request.user)
        return Response({
            'message': f'Redeemed {ser.validated_data["points"]} points for ₹{discount_rupees} discount.',
            'points_redeemed': ser.validated_data['points'],
            'discount_rupees': discount_rupees,
            'balance_remaining': account.balance,
        })


class WalletWithdrawalRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Wallet'],
        summary='List wallet withdrawal requests',
        responses={200: WalletWithdrawalRequestSerializer(many=True)},
    )
    def get(self, request):
        qs = WalletWithdrawalRequest.objects.filter(user=request.user)
        paginator = StandardOffsetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(WalletWithdrawalRequestSerializer(page, many=True).data)

    @extend_schema(
        tags=['Wallet'],
        summary='Submit a wallet withdrawal request',
        request=WalletWithdrawalRequestSerializer,
        responses={201: WalletWithdrawalRequestSerializer},
    )
    def post(self, request):
        ser = WalletWithdrawalRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=drf_status.HTTP_400_BAD_REQUEST)
        ser.save(user=request.user)
        return Response(ser.data, status=drf_status.HTTP_201_CREATED)


class WalletTopupInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Wallet'],
        summary='Initiate wallet top-up via Razorpay',
        description='Creates a Razorpay order for the given amount (in INR). Returns order details and Razorpay key for client-side checkout.',
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        try:
            amount_inr = int(request.data.get('amount', 0))
        except (TypeError, ValueError):
            return Response({'error': 'invalid_amount', 'message': 'Amount must be a positive integer (INR).'}, status=400)

        if amount_inr < 10:
            return Response({'error': 'invalid_amount', 'message': 'Minimum top-up is ₹10.'}, status=400)
        if amount_inr > 10000:
            return Response({'error': 'invalid_amount', 'message': 'Maximum top-up is ₹10,000 per transaction.'}, status=400)

        try:
            import razorpay
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order = client.order.create({
                'amount': amount_inr * 100,  # paise
                'currency': 'INR',
                'receipt': f'topup_{request.user.id}',
                'notes': {'user_id': str(request.user.id), 'purpose': 'wallet_topup'},
            })
        except Exception as exc:
            logger.exception('Razorpay order creation failed: %s', exc)
            return Response({'error': 'payment_gateway_error', 'message': 'Could not initiate payment. Try again.'}, status=502)

        return Response({
            'order_id': order['id'],
            'amount': amount_inr,
            'amount_paise': amount_inr * 100,
            'currency': 'INR',
            'key': settings.RAZORPAY_KEY_ID,
            'points_to_credit': amount_inr * POINTS_PER_RUPEE,
        })


class WalletTopupVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Wallet'],
        summary='Verify Razorpay payment and credit wallet',
        description=(
            'Verifies the Razorpay payment signature. On success, credits '
            'amount × 10 loyalty points to the user wallet. '
            'Idempotent — duplicate payment IDs are rejected.'
        ),
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        payment_id = request.data.get('razorpay_payment_id', '')
        order_id   = request.data.get('razorpay_order_id', '')
        signature  = request.data.get('razorpay_signature', '')
        amount_inr = request.data.get('amount')

        if not all([payment_id, order_id, signature, amount_inr]):
            return Response({'error': 'missing_fields', 'message': 'razorpay_payment_id, razorpay_order_id, razorpay_signature, and amount are required.'}, status=400)

        try:
            amount_inr = int(amount_inr)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_amount'}, status=400)

        # Verify signature: HMAC-SHA256(order_id + "|" + payment_id, secret)
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f'{order_id}|{payment_id}'.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            return Response({'error': 'invalid_signature', 'message': 'Payment verification failed.'}, status=400)

        # Idempotency: check if this payment_id was already used
        already_credited = LoyaltyTransaction.objects.filter(
            account__user=request.user,
            description__contains=payment_id,
        ).exists()
        if already_credited:
            return Response({'error': 'already_credited', 'message': 'This payment has already been credited.'}, status=400)

        points = amount_inr * POINTS_PER_RUPEE
        try:
            from django.db import transaction as db_transaction
            with db_transaction.atomic():
                account = LoyaltyService.get_account(request.user)
                LoyaltyService._add_points(
                    account=account,
                    points=points,
                    source=LoyaltyTransaction.SOURCE_EARNED,
                    description=f'Wallet top-up ₹{amount_inr} | {payment_id}',
                )
                account.refresh_from_db(fields=['balance'])
        except Exception as exc:
            logger.exception('Failed to credit wallet after payment %s: %s', payment_id, exc)
            return Response({'error': 'credit_failed', 'message': 'Payment verified but wallet credit failed. Contact support.'}, status=500)

        account = LoyaltyService.get_account(request.user)
        return Response({
            'message': f'₹{amount_inr} added to wallet. {points} points credited.',
            'points_credited': points,
            'new_balance': account.balance,
        })
