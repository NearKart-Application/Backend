"""
NearKart — Analytics Views
Vendor-only endpoints that aggregate store performance data.
"""
import logging
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.permissions import IsVendor
from apps.videos.models import Video
from apps.products.models import Product
from apps.billing.services import BillingService
from .serializers import VideoStatSerializer, ProductStatSerializer

logger = logging.getLogger(__name__)


class VendorDashboardView(APIView):
    """GET /analytics/vendor/ — full store performance dashboard."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        summary='Vendor Dashboard',
        description='Returns a full performance summary for the authenticated vendor\'s store.',
        tags=['Analytics'],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        try:
            store = request.user.store
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)

        # ── Subscription & wallet ──
        plan = BillingService.get_active_plan(store)
        sub  = BillingService.get_subscription(store)

        subscription_data = None
        if sub:
            subscription_data = {
                'plan':       plan.display_name,
                'expires_at': sub.expires_at,
                'is_active':  sub.is_active,
                'days_left':  max(0, (sub.expires_at - timezone.now()).days) if sub.is_active else 0,
            }

        # ── Products ──
        products_qs = store.products.all()
        product_counts = products_qs.aggregate(
            total    = Count('id'),
            active   = Count('id', filter=Q(status='active')),
            draft    = Count('id', filter=Q(status='draft')),
            inactive = Count('id', filter=Q(status='inactive')),
        )

        # ── Videos ──
        videos_qs = store.videos.all()
        video_counts = videos_qs.aggregate(
            total      = Count('id'),
            ready      = Count('id', filter=Q(status='ready')),
            processing = Count('id', filter=Q(status='processing')),
            pending    = Count('id', filter=Q(status='pending_upload')),
            total_likes= Sum('like_count'),
            total_views= Sum('view_count'),
        )

        # ── Store social ──
        follower_count = store.followers.count()
        review_count   = store.reviews.count()
        avg_rating     = store.reviews.aggregate(avg=Avg('rating'))['avg'] or 0

        return Response({
            'store': {
                'id':            str(store.id),
                'name':          store.name,
                'category':      store.category,
                'is_active':     store.is_active,
                'is_verified':   store.is_verified,
                'is_open':       store.is_open,
                'follower_count': follower_count,
                'review_count':   review_count,
                'avg_rating':     round(float(avg_rating), 2),
            },
            'wallet': {
                'balance': str(store.wallet_balance),
            },
            'subscription': subscription_data,
            'current_plan': {
                'name':          plan.name,
                'display_name':  plan.display_name,
                'video_limit':   plan.video_limit,
                'product_limit': plan.product_limit,
            },
            'products': {
                'total':    product_counts['total'],
                'active':   product_counts['active'],
                'draft':    product_counts['draft'],
                'inactive': product_counts['inactive'],
            },
            'videos': {
                'total':       video_counts['total'],
                'ready':       video_counts['ready'],
                'processing':  video_counts['processing'],
                'pending':     video_counts['pending'],
                'total_likes': video_counts['total_likes'] or 0,
                'total_views': video_counts['total_views'] or 0,
            },
        })


class VendorVideoStatsView(APIView):
    """GET /analytics/vendor/videos/ — per-video engagement stats."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        summary='Vendor Video Stats',
        description='Returns all vendor videos with view and like counts, ordered by most views.',
        tags=['Analytics'],
        responses={200: VideoStatSerializer(many=True)},
    )
    def get(self, request):
        try:
            store = request.user.store
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)

        videos = store.videos.order_by('-view_count', '-created_at')
        return Response(VideoStatSerializer(videos, many=True).data)


class VendorProductStatsView(APIView):
    """GET /analytics/vendor/products/ — per-product wishlist engagement stats."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        summary='Vendor Product Stats',
        description='Returns all vendor products with wishlist counts, ordered by most wishlisted.',
        tags=['Analytics'],
        responses={200: ProductStatSerializer(many=True)},
    )
    def get(self, request):
        try:
            store = request.user.store
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)

        products = store.products.prefetch_related('wishlisted_by').order_by('-created_at')
        return Response(ProductStatSerializer(products, many=True).data)
