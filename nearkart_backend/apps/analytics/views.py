"""
NearKart — Analytics Views
Vendor-only endpoints that aggregate store performance data.
"""
import csv
import io
import logging
from decimal import Decimal
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.pagination import StandardOffsetPagination
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
        if sub and plan:
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
                'name':          plan.name          if plan else 'free',
                'display_name':  plan.display_name  if plan else 'Free',
                'video_limit':   plan.video_limit   if plan else 0,
                'product_limit': plan.product_limit if plan else 0,
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
        paginator = StandardOffsetPagination()
        page = paginator.paginate_queryset(videos, request)
        return paginator.get_paginated_response(VideoStatSerializer(page, many=True).data)


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

        products = store.products.prefetch_related('wishlisted_by', 'reservations').order_by('-created_at')
        return Response(ProductStatSerializer(products, many=True).data)


class VendorTimeSeriesView(APIView):
    """GET /analytics/vendor/timeseries/?days=30 — daily snapshot trend data."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(summary='Vendor Time-Series Analytics', tags=['Analytics'], responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        try:
            store = request.user.store
        except Exception:
            return Response({'error': 'no_store'}, status=400)

        try:
            days = max(7, min(90, int(request.query_params.get('days', 30))))
        except (TypeError, ValueError):
            days = 30

        import datetime
        from .models import DailyAnalyticsSnapshot
        since = timezone.now().date() - datetime.timedelta(days=days)
        snapshots = DailyAnalyticsSnapshot.objects.filter(
            store=store, snapshot_date__gte=since
        ).order_by('snapshot_date')

        rows = []
        for s in snapshots:
            rows.append({
                'date':              str(s.snapshot_date),
                'reservation_count': s.reservation_count,
                'completed_count':   s.completed_count,
                'revenue':           str(s.revenue),
                'follower_count':    s.follower_count,
                'new_customer_count': s.new_customer_count,
            })
        return Response({'days': days, 'data': rows})


class VendorRevenueView(APIView):
    """GET /analytics/vendor/revenue/?period=30 — revenue summary from completed reservations."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(summary='Vendor Revenue Summary', tags=['Analytics'], responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        try:
            store = request.user.store
        except Exception:
            return Response({'error': 'no_store'}, status=400)

        try:
            days = max(7, min(365, int(request.query_params.get('period', 30))))
        except (TypeError, ValueError):
            days = 30

        import datetime
        from apps.reservations.models import Reservation, ReservationStatus
        since = timezone.now() - datetime.timedelta(days=days)
        completed = Reservation.objects.filter(
            store=store,
            status=ReservationStatus.COMPLETED,
            updated_at__gte=since,
        )

        total_revenue  = completed.aggregate(s=Sum('actual_selling_price'))['s'] or Decimal('0')
        total_orders   = completed.count()
        avg_order_val  = (total_revenue / total_orders) if total_orders > 0 else Decimal('0')

        # Top products by revenue
        from apps.reservations.models import Reservation as R
        top_products = (
            completed.filter(actual_selling_price__isnull=False)
            .values('product__name')
            .annotate(revenue=Sum('actual_selling_price'), count=Count('id'))
            .order_by('-revenue')[:5]
        )

        return Response({
            'period_days':     days,
            'total_revenue':   str(total_revenue),
            'total_orders':    total_orders,
            'avg_order_value': str(round(avg_order_val, 2)),
            'top_products': [
                {'name': p['product__name'], 'revenue': str(p['revenue']), 'count': p['count']}
                for p in top_products
            ],
        })


class VendorCustomerStatsView(APIView):
    """GET /analytics/vendor/customers/ — customer demographics from reservations."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(summary='Vendor Customer Demographics', tags=['Analytics'], responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        try:
            store = request.user.store
        except Exception:
            return Response({'error': 'no_store'}, status=400)

        from apps.reservations.models import Reservation, ReservationStatus

        all_res = Reservation.objects.filter(store=store)
        completed = all_res.filter(status=ReservationStatus.COMPLETED)

        total_customers = all_res.values('customer').distinct().count()
        returning = all_res.values('customer').annotate(c=Count('id')).filter(c__gt=1).count()
        new_customers = total_customers - returning

        # Customers this month
        import datetime
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month = all_res.filter(created_at__gte=month_start).values('customer').distinct().count()

        return Response({
            'total_customers':     total_customers,
            'new_customers':       new_customers,
            'returning_customers': returning,
            'customers_this_month': this_month,
            'total_completed':     completed.count(),
        })


class VendorAnalyticsExportView(APIView):
    """GET /analytics/vendor/export/ — download 30-day analytics snapshot as CSV."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(summary='Export analytics CSV', tags=['Analytics'])
    def get(self, request):
        try:
            store = request.user.store
        except Exception:
            return Response({'error': 'no_store'}, status=400)

        import datetime
        from .models import DailyAnalyticsSnapshot
        since = timezone.now().date() - datetime.timedelta(days=30)
        snapshots = DailyAnalyticsSnapshot.objects.filter(
            store=store, snapshot_date__gte=since
        ).order_by('snapshot_date')

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Reservations', 'Completed', 'Revenue (₹)', 'Followers', 'New Customers'])
        for s in snapshots:
            writer.writerow([
                s.snapshot_date, s.reservation_count, s.completed_count,
                s.revenue, s.follower_count, s.new_customer_count,
            ])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="analytics_{store.name}_{timezone.now().date()}.csv"'
        return response
