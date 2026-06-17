"""
NearKart — Loyalty Views

GET  /loyalty/           → balance + referral code
GET  /loyalty/history/   → transaction list
POST /loyalty/apply-referral/ → apply someone's referral code (one-time)
POST /loyalty/redeem/    → redeem points (returns discount in rupees)
"""
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.pagination import StandardOffsetPagination
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from .models import LoyaltyTransaction
from .serializers import (
    LoyaltyBalanceSerializer,
    LoyaltyTransactionSerializer,
    ApplyReferralSerializer,
    RedeemPointsSerializer,
)
from .services import LoyaltyService

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
