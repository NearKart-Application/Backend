"""
NearKart — Admin Panel Views
All endpoints require is_staff=True (Django staff / superuser).
"""
import logging
from django.db.models import Count, Sum, Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.stores.models import Store
from apps.auth_app.models import User
from apps.videos.models import Video
from apps.products.models import Product
from apps.billing.models import Transaction
from .serializers import AdminStoreSerializer, AdminStoreUpdateSerializer, AdminUserSerializer

logger = logging.getLogger(__name__)


class PlatformStatsView(APIView):
    """GET /admin-panel/stats/ — platform-wide aggregated statistics."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='Platform Statistics',
        description='Returns aggregated platform metrics. Staff access only.',
        tags=['Admin Panel'],
    )
    def get(self, request):
        user_counts = User.objects.aggregate(
            total     = Count('id'),
            vendors   = Count('id', filter=Q(role='vendor')),
            customers = Count('id', filter=Q(role='customer')),
            active    = Count('id', filter=Q(is_active=True)),
        )

        store_counts = Store.objects.aggregate(
            total    = Count('id'),
            active   = Count('id', filter=Q(is_active=True)),
            verified = Count('id', filter=Q(is_verified=True)),
            open     = Count('id', filter=Q(is_open=True)),
        )

        video_counts = Video.objects.aggregate(
            total      = Count('id'),
            ready      = Count('id', filter=Q(status='ready')),
            total_views= Sum('view_count'),
            total_likes= Sum('like_count'),
        )

        product_count = Product.objects.filter(status='active').count()

        revenue = Transaction.objects.filter(
            type='subscription'
        ).aggregate(total=Sum('amount'))['total'] or 0

        topup_total = Transaction.objects.filter(
            type='topup'
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'users': {
                'total':     user_counts['total'],
                'vendors':   user_counts['vendors'],
                'customers': user_counts['customers'],
                'active':    user_counts['active'],
            },
            'stores': {
                'total':    store_counts['total'],
                'active':   store_counts['active'],
                'verified': store_counts['verified'],
                'open':     store_counts['open'],
            },
            'videos': {
                'total':       video_counts['total'],
                'ready':       video_counts['ready'],
                'total_views': video_counts['total_views'] or 0,
                'total_likes': video_counts['total_likes'] or 0,
            },
            'products': {
                'active': product_count,
            },
            'revenue': {
                'subscription_revenue': str(abs(revenue)),
                'total_topups':         str(topup_total),
            },
        })


class AdminStoreListView(APIView):
    """GET /admin-panel/stores/ — paginated list of all stores with search."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='List All Stores (Admin)',
        description='Returns all stores. Supports ?search=, ?is_active=, ?is_verified=, ?category= filters.',
        tags=['Admin Panel'],
        parameters=[
            OpenApiParameter('search',      str,  description='Filter by store name (partial match)'),
            OpenApiParameter('is_active',   bool, description='Filter by active status'),
            OpenApiParameter('is_verified', bool, description='Filter by verified status'),
            OpenApiParameter('category',    str,  description='Filter by category slug'),
        ],
    )
    def get(self, request):
        qs = Store.objects.select_related('owner').order_by('-created_at')

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(owner__phone_number__icontains=search)
            )

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        is_verified = request.query_params.get('is_verified')
        if is_verified is not None:
            qs = qs.filter(is_verified=is_verified.lower() == 'true')

        category = request.query_params.get('category', '').strip()
        if category:
            qs = qs.filter(category=category)

        serializer = AdminStoreSerializer(qs, many=True)
        return Response({'count': qs.count(), 'results': serializer.data})


class AdminStoreUpdateView(APIView):
    """PATCH /admin-panel/stores/<store_id>/ — update is_verified / is_active / is_open."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='Update Store (Admin)',
        description='Update is_verified, is_active, or is_open for any store. Staff access only.',
        tags=['Admin Panel'],
        request=AdminStoreUpdateSerializer,
    )
    def patch(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=404)

        serializer = AdminStoreUpdateSerializer(store, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()
        logger.info(f'[admin] store {store.id} updated by staff {request.user.id}: {request.data}')
        return Response(AdminStoreSerializer(store).data)


class AdminUserListView(APIView):
    """GET /admin-panel/users/ — paginated list of all users."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='List All Users (Admin)',
        description='Returns all users. Supports ?search=, ?role=, ?is_active= filters.',
        tags=['Admin Panel'],
        parameters=[
            OpenApiParameter('search',    str,  description='Filter by phone or name (partial match)'),
            OpenApiParameter('role',      str,  description='Filter by role: vendor, customer, admin'),
            OpenApiParameter('is_active', bool, description='Filter by active status'),
        ],
    )
    def get(self, request):
        qs = User.objects.order_by('-created_at')

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(phone_number__icontains=search) | Q(full_name__icontains=search)
            )

        role = request.query_params.get('role', '').strip()
        if role:
            qs = qs.filter(role=role)

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        serializer = AdminUserSerializer(qs, many=True)
        return Response({'count': qs.count(), 'results': serializer.data})


class AdminUserToggleActiveView(APIView):
    """POST /admin-panel/users/<user_id>/toggle-active/ — enable or disable a user."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='Toggle User Active (Admin)',
        description='Flips is_active on a user account. Cannot disable your own account.',
        tags=['Admin Panel'],
    )
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'User not found.'}, status=404)

        if user.id == request.user.id:
            return Response({'error': 'forbidden', 'message': 'Cannot deactivate your own account.'}, status=400)

        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])

        action = 'activated' if user.is_active else 'deactivated'
        logger.info(f'[admin] user {user.id} {action} by staff {request.user.id}')
        return Response({
            'message':   f'User {action} successfully.',
            'user_id':   str(user.id),
            'is_active': user.is_active,
        })
