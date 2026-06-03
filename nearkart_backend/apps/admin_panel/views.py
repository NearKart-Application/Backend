"""
NearKart — Admin Panel Views
"""
import logging
from django.db.models import Count, Sum, Q
from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.permissions import IsAdmin, IsMasterAdmin
from apps.stores.models import Store, WebsiteRequest
from apps.auth_app.models import User, UserRole
from .models import PromoBanner, AdminActivityLog, Category, OfferTemplate
from apps.videos.models import Video
from apps.products.models import Product
from apps.billing.models import Transaction
from .serializers import (
    AdminStoreSerializer, AdminStoreUpdateSerializer, AdminUserSerializer,
    AdminProductSerializer, AdminWebsiteRequestSerializer,
    CategorySerializer, CategoryCreateSerializer, OfferTemplateSerializer,
)

logger = logging.getLogger(__name__)


def _city_scope(user) -> list:
    """Return list of assigned cities for location admins; empty list means no filter (master_admin sees all)."""
    if user.role == 'master_admin':
        return []
    raw = getattr(user, 'admin_assigned_city', '') or ''
    return [c.strip() for c in raw.split(',') if c.strip()]


def _city_q(cities: list, *field_paths: str):
    """Build an OR Q combining all cities across all field paths with icontains."""
    q = Q()
    for field in field_paths:
        for city in cities:
            q |= Q(**{f'{field}__icontains': city})
    return q


class PlatformStatsView(APIView):
    """GET /admin-panel/stats/ — platform-wide aggregated statistics."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='Platform Statistics',
        description='Returns aggregated platform metrics. Staff access only.',
        tags=['Admin Panel'],
        responses={200: OpenApiTypes.OBJECT},
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
        pending_website_requests = WebsiteRequest.objects.filter(status='pending').count()

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
            'pending_website_requests': pending_website_requests,
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
        responses={200: AdminStoreSerializer(many=True)},
    )
    def get(self, request):
        qs = Store.objects.select_related('owner').order_by('-created_at')

        cities = _city_scope(request.user)
        if cities:
            qs = qs.filter(_city_q(cities, 'locality', 'address'))

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
        responses={200: AdminStoreSerializer},
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
        _log_action(request.user, 'update_store', 'store', str(store.id), store.name, str(request.data))
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
        responses={200: AdminUserSerializer(many=True)},
    )
    def get(self, request):
        qs = User.objects.order_by('-created_at')

        cities = _city_scope(request.user)
        if cities:
            # Location admins see vendors with stores in any of their assigned cities, plus all admins.
            qs = qs.filter(
                _city_q(cities, 'stores__locality') & Q(role='vendor') |
                Q(role__in=('admin', 'master_admin'))
            ).distinct()

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(phone_number__icontains=search) |
                Q(full_name__icontains=search) |
                Q(profile_id__icontains=search)
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
        request=None,
        responses={200: OpenApiTypes.OBJECT},
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
        _log_action(request.user, f'toggle_user_{action}', 'user', str(user.id), user.phone_number)
        logger.info(f'[admin] user {user.id} {action} by staff {request.user.id}')
        return Response({
            'message':   f'User {action} successfully.',
            'user_id':   str(user.id),
            'is_active': user.is_active,
        })


# ── Public Banners ─────────────────────────────────────────────────────────────

class PublicBannersView(APIView):
    """GET /admin-panel/banners/active/ — active, scheduled banners for home screen."""
    permission_classes = [AllowAny]

    def get(self, request):
        now = timezone.now()
        banners = PromoBanner.objects.filter(
            is_active=True,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now)
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=now)
        ).order_by('display_order', '-created_at')

        data = [_banner_to_dict(b) for b in banners]
        return Response({'count': len(data), 'results': data})


# ── Admin Banner CRUD ──────────────────────────────────────────────────────────

class AdminBannerListCreateView(APIView):
    """GET/POST /admin-panel/banners/ — list all or create a banner."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        banners = PromoBanner.objects.all().order_by('display_order', '-created_at')
        return Response({'count': banners.count(), 'results': [_banner_to_dict(b) for b in banners]})

    def post(self, request):
        data = request.data
        required = ['title']
        for f in required:
            if not data.get(f):
                return Response({'error': 'validation_error', 'message': f'{f} is required.'}, status=400)

        banner = PromoBanner.objects.create(
            title         = data['title'].strip(),
            subtitle      = data.get('subtitle', '').strip(),
            badge_text    = data.get('badge_text', '').strip(),
            image_url     = data.get('image_url', '').strip(),
            link_type     = data.get('link_type', PromoBanner.LINK_NONE),
            link_value    = data.get('link_value', '').strip(),
            display_order = int(data.get('display_order', 0)),
            is_active     = bool(data.get('is_active', True)),
            starts_at     = data.get('starts_at') or None,
            ends_at       = data.get('ends_at') or None,
            is_paid       = bool(data.get('is_paid', False)),
            created_by    = request.user,
        )
        return Response(_banner_to_dict(banner), status=201)


class AdminBannerDetailView(APIView):
    """PATCH/DELETE /admin-panel/banners/<id>/ — update or delete a banner."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, banner_id):
        try:
            banner = PromoBanner.objects.get(id=banner_id)
        except PromoBanner.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)

        data = request.data
        for field in ['title', 'subtitle', 'badge_text', 'image_url', 'link_type', 'link_value']:
            if field in data:
                setattr(banner, field, str(data[field]).strip())
        if 'display_order' in data:
            banner.display_order = int(data['display_order'])
        if 'is_active' in data:
            banner.is_active = bool(data['is_active'])
        if 'is_paid' in data:
            banner.is_paid = bool(data['is_paid'])
        if 'starts_at' in data:
            banner.starts_at = data['starts_at'] or None
        if 'ends_at' in data:
            banner.ends_at = data['ends_at'] or None
        banner.save()
        return Response(_banner_to_dict(banner))

    def delete(self, request, banner_id):
        try:
            banner = PromoBanner.objects.get(id=banner_id)
        except PromoBanner.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        banner.delete()
        return Response(status=204)


class AdminBannerToggleView(APIView):
    """POST /admin-panel/banners/<id>/toggle/ — flip is_active."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, banner_id):
        try:
            banner = PromoBanner.objects.get(id=banner_id)
        except PromoBanner.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        banner.is_active = not banner.is_active
        banner.save(update_fields=['is_active', 'updated_at'])
        return Response({'id': str(banner.id), 'is_active': banner.is_active})


# ── Master Admin — Manage Admin Users ─────────────────────────────────────────

class AdminUserManageView(APIView):
    """GET/POST /admin-panel/admins/ — list or create admin users (master only)."""
    permission_classes = [IsAuthenticated, IsMasterAdmin]

    def get(self, request):
        admins = User.objects.filter(role=UserRole.ADMIN).order_by('-created_at')
        return Response({
            'count': admins.count(),
            'results': [_admin_user_dict(u) for u in admins],
        })

    def post(self, request):
        phone = request.data.get('phone_number', '').strip()
        name  = request.data.get('full_name', '').strip()
        city  = request.data.get('admin_assigned_city', '').strip()
        if not phone:
            return Response({'error': 'validation_error', 'message': 'phone_number is required.'}, status=400)
        if not city:
            return Response({'error': 'validation_error', 'message': 'admin_assigned_city is required.'}, status=400)

        if User.objects.filter(phone_number=phone).exists():
            user = User.objects.get(phone_number=phone)
            if user.role in (UserRole.MASTER_ADMIN,):
                return Response({'error': 'forbidden', 'message': 'Cannot change master admin role.'}, status=403)
            user.role                = UserRole.ADMIN
            user.is_staff            = True
            user.admin_assigned_city = city
            if name:
                user.full_name = name
            user.save(update_fields=['role', 'is_staff', 'full_name', 'admin_assigned_city', 'updated_at'])
        else:
            user = User.objects.create_user(
                phone_number=phone,
                role=UserRole.ADMIN,
                full_name=name,
                is_staff=True,
                admin_assigned_city=city,
            )
        return Response(_admin_user_dict(user), status=201)


class AdminUserDeleteView(APIView):
    """PATCH/DELETE /admin-panel/admins/<user_id>/ — update or remove admin (master only)."""
    permission_classes = [IsAuthenticated, IsMasterAdmin]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        if user.role == UserRole.MASTER_ADMIN:
            return Response({'error': 'forbidden', 'message': 'Cannot edit master admin.'}, status=403)
        update_fields = ['updated_at']
        if 'full_name' in request.data:
            user.full_name = request.data['full_name'].strip()
            update_fields.append('full_name')
        if 'admin_assigned_city' in request.data:
            user.admin_assigned_city = request.data['admin_assigned_city'].strip()
            update_fields.append('admin_assigned_city')
        user.save(update_fields=update_fields)
        return Response(_admin_user_dict(user))

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        if user.role == UserRole.MASTER_ADMIN:
            return Response({'error': 'forbidden', 'message': 'Cannot remove master admin.'}, status=403)
        user.role     = UserRole.CUSTOMER
        user.is_staff = False
        user.save(update_fields=['role', 'is_staff', 'updated_at'])
        return Response({'message': f'{user.phone_number} removed from admins.'})


# ── Admin Product Management ───────────────────────────────────────────────────

class AdminProductListView(APIView):
    """GET /admin-panel/products/ — list all products across all stores."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='List All Products (Admin)',
        description='Returns all products. Supports ?search=, ?status=, ?store_id= filters.',
        tags=['Admin Panel'],
        parameters=[
            OpenApiParameter('search',   str, description='Filter by product name (partial match)'),
            OpenApiParameter('status',   str, description='Filter by status: active, draft, inactive, out_of_stock'),
            OpenApiParameter('store_id', str, description='Filter by store UUID'),
        ],
        responses={200: AdminProductSerializer(many=True)},
    )
    def get(self, request):
        qs = Product.objects.select_related('store').prefetch_related('images', 'variants').order_by('-created_at')

        cities = _city_scope(request.user)
        if cities:
            qs = qs.filter(_city_q(cities, 'store__locality', 'store__address'))

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(store__name__icontains=search))

        status_filter = request.query_params.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        store_id = request.query_params.get('store_id', '').strip()
        if store_id:
            qs = qs.filter(store_id=store_id)

        serializer = AdminProductSerializer(qs, many=True)
        return Response({'count': qs.count(), 'results': serializer.data})


class AdminProductDetailView(APIView):
    """PATCH /admin-panel/products/<product_id>/ — update product status / visibility."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='Update Product (Admin)',
        description='Update status or is_visible for any product.',
        tags=['Admin Panel'],
        request=AdminProductSerializer,
        responses={200: AdminProductSerializer},
    )
    def patch(self, request, product_id):
        try:
            product = Product.objects.select_related('store').get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=404)

        allowed_fields = ['status', 'is_visible']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        serializer = AdminProductSerializer(product, data=data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()
        logger.info(f'[admin] product {product.id} updated by staff {request.user.id}: {data}')
        return Response(AdminProductSerializer(product).data)


# ── Admin Website Request Management ──────────────────────────────────────────

class AdminWebsiteRequestListView(APIView):
    """GET /admin-panel/website-requests/ — list all vendor website requests."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='List Website Requests (Admin)',
        description='Returns all website requests. Supports ?status= filter.',
        tags=['Admin Panel'],
        parameters=[
            OpenApiParameter('status', str, description='Filter by status: pending, approved, rejected'),
        ],
        responses={200: AdminWebsiteRequestSerializer(many=True)},
    )
    def get(self, request):
        qs = WebsiteRequest.objects.select_related('store').order_by('-created_at')

        status_filter = request.query_params.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        serializer = AdminWebsiteRequestSerializer(qs, many=True)
        return Response({'count': qs.count(), 'results': serializer.data})


class AdminWebsiteRequestUpdateView(APIView):
    """PATCH /admin-panel/website-requests/<request_id>/ — approve or reject."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='Update Website Request (Admin)',
        description='Approve or reject a vendor website request. Set status + admin_notes.',
        tags=['Admin Panel'],
        request=AdminWebsiteRequestSerializer,
        responses={200: AdminWebsiteRequestSerializer},
    )
    def patch(self, request, request_id):
        try:
            wr = WebsiteRequest.objects.select_related('store').get(id=request_id)
        except WebsiteRequest.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Website request not found.'}, status=404)

        new_status = request.data.get('status', '').strip()
        if new_status and new_status not in (WebsiteRequest.STATUS_PENDING, WebsiteRequest.STATUS_APPROVED, WebsiteRequest.STATUS_REJECTED):
            return Response({'error': 'validation_error', 'message': f'Invalid status: {new_status}'}, status=400)

        if new_status:
            wr.status = new_status
            if new_status != WebsiteRequest.STATUS_PENDING:
                wr.reviewed_at = timezone.now()

        admin_notes = request.data.get('admin_notes')
        if admin_notes is not None:
            wr.admin_notes = admin_notes.strip()

        wr.save()
        logger.info(f'[admin] website_request {wr.id} updated to {wr.status} by staff {request.user.id}')
        return Response(AdminWebsiteRequestSerializer(wr).data)


# ── Admin Create User ──────────────────────────────────────────────────────────

class AdminCreateUserView(APIView):
    """POST /admin-panel/users/create/ — create a new user account."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='Create User (Admin)',
        description='Create a new user account. Admin can set role (customer/vendor). city_scope enforced.',
        tags=['Admin Panel'],
        request=None,
        responses={201: AdminUserSerializer},
    )
    def post(self, request):
        phone = request.data.get('phone_number', '').strip()
        role  = request.data.get('role', 'customer').strip()
        name  = request.data.get('full_name', '').strip()

        if not phone:
            return Response({'error': 'validation_error', 'message': 'phone_number is required.'}, status=400)
        if role not in ('customer', 'vendor'):
            return Response({'error': 'validation_error', 'message': 'role must be customer or vendor.'}, status=400)

        if User.objects.filter(phone_number=phone).exists():
            return Response({'error': 'conflict', 'message': 'User with this phone number already exists.'}, status=409)

        user = User.objects.create_user(phone_number=phone, role=role, full_name=name)
        _log_action(request.user, 'create_user', 'user', str(user.id),
                    user.phone_number, f'role={role}')
        return Response(AdminUserSerializer(user).data, status=201)


# ── Admin Suspend / Unsuspend User ─────────────────────────────────────────────

class AdminUserSuspendView(APIView):
    """POST /admin-panel/users/<user_id>/suspend/ — suspend or unsuspend a user."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='Suspend / Unsuspend User (Admin)',
        description='Set is_suspended=true/false. Provide reason when suspending.',
        tags=['Admin Panel'],
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'User not found.'}, status=404)

        if user.id == request.user.id:
            return Response({'error': 'forbidden', 'message': 'Cannot suspend your own account.'}, status=400)

        suspend = bool(request.data.get('suspend', True))
        reason  = request.data.get('reason', '').strip()

        if suspend and not reason:
            return Response({'error': 'validation_error', 'message': 'reason is required when suspending.'}, status=400)

        user.is_suspended = suspend
        user.suspension_reason = reason if suspend else ''
        user.save(update_fields=['is_suspended', 'suspension_reason', 'updated_at'])

        action = 'suspend_user' if suspend else 'unsuspend_user'
        _log_action(request.user, action, 'user', str(user.id), user.phone_number, reason)
        return Response({
            'message':      f'User {"suspended" if suspend else "unsuspended"} successfully.',
            'user_id':      str(user.id),
            'is_suspended': user.is_suspended,
        })


# ── Admin Store Video Management ───────────────────────────────────────────────

class AdminStoreVideoListView(APIView):
    """GET /admin-panel/stores/<store_id>/videos/ — list all videos for a store."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='List Store Videos (Admin)',
        description='Returns all videos for a specific store, ordered by upload date.',
        tags=['Admin Panel'],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=404)

        videos = Video.objects.filter(store=store).order_by('-created_at')
        data = [_video_to_dict(v) for v in videos]
        return Response({'count': len(data), 'store_id': str(store.id), 'store_name': store.name, 'results': data})


class AdminDeleteVideoView(APIView):
    """DELETE /admin-panel/videos/<video_id>/ — delete a video."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='Delete Video (Admin)',
        description='Permanently delete a video. Use for suspicious or policy-violating content.',
        tags=['Admin Panel'],
        request=None,
        responses={204: None},
    )
    def delete(self, request, video_id):
        try:
            video = Video.objects.select_related('store').get(id=video_id)
        except Video.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Video not found.'}, status=404)

        store_name = video.store.name
        title      = video.title
        _log_action(request.user, 'delete_video', 'video', str(video.id),
                    f'{title} ({store_name})', f'store_id={video.store_id}')
        video.delete()
        logger.info(f'[admin] video {video_id} deleted by staff {request.user.id}')
        return Response(status=204)


# ── Admin Activity Log ─────────────────────────────────────────────────────────

class AdminActivityLogView(APIView):
    """GET/POST /admin-panel/activity-log/ — admin action log."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary='Admin Activity Log',
        description='Returns the 100 most recent admin actions, newest first.',
        tags=['Admin Panel'],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        qs = AdminActivityLog.objects.select_related('admin').order_by('-created_at')[:100]
        results = [
            {
                'id':           str(e.id),
                'admin_phone':  e.admin.phone_number if e.admin else '',
                'admin_name':   e.admin.full_name    if e.admin else '',
                'action':       e.action,
                'target_type':  e.target_type,
                'target_id':    e.target_id,
                'target_label': e.target_label,
                'detail':       e.detail,
                'created_at':   e.created_at.isoformat(),
            }
            for e in qs
        ]
        return Response({'count': len(results), 'results': results})

    @extend_schema(
        summary='Create Activity Log Entry',
        description='Records an admin action. Sent by mobile after add/remove/update admin operations.',
        tags=['Admin Panel'],
        responses={201: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        action       = request.data.get('action', '').strip()
        target_type  = request.data.get('target_type', '').strip()
        target_id    = request.data.get('target_id', '').strip()
        target_label = request.data.get('target_label', '').strip()
        detail       = request.data.get('detail', '').strip()
        if not action:
            return Response({'error': 'validation_error', 'message': 'action is required.'}, status=400)
        _log_action(
            admin=request.user,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_label=target_label,
            detail=detail,
        )
        return Response({'message': 'Logged.'}, status=201)


# ── Category Management ────────────────────────────────────────────────────────

class AdminCategoryListCreateView(APIView):
    """GET/POST /admin-panel/categories/ — list all or create a category (admin only)."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        categories = Category.objects.all().order_by('display_order', 'name')
        serializer = CategorySerializer(categories, many=True)
        return Response({'count': categories.count(), 'results': serializer.data})

    def post(self, request):
        data = request.data
        name = data.get('name', '').strip()
        if not name:
            return Response({'error': 'validation_error', 'message': 'name is required.'}, status=400)

        # Auto-generate slug from name if not provided
        slug = data.get('slug', '').strip()
        if not slug:
            slug = name.lower().replace(' ', '-')

        if Category.objects.filter(name__iexact=name).exists():
            return Response({'error': 'conflict', 'message': 'A category with this name already exists.'}, status=409)
        if Category.objects.filter(slug=slug).exists():
            return Response({'error': 'conflict', 'message': 'A category with this slug already exists.'}, status=409)

        category = Category.objects.create(
            name          = name,
            slug          = slug,
            icon          = data.get('icon', '').strip(),
            display_order = int(data.get('display_order', 0)),
            is_active     = bool(data.get('is_active', True)),
            created_by    = request.user,
        )
        return Response(CategorySerializer(category).data, status=201)


class AdminCategoryDetailView(APIView):
    """PUT/PATCH/DELETE /admin-panel/categories/<category_id>/"""
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_category(self, category_id):
        try:
            return Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return None

    def put(self, request, category_id):
        category = self._get_category(category_id)
        if not category:
            return Response({'error': 'not_found'}, status=404)

        data = request.data
        name = data.get('name', '').strip()
        if not name:
            return Response({'error': 'validation_error', 'message': 'name is required.'}, status=400)

        slug = data.get('slug', '').strip() or name.lower().replace(' ', '-')

        # Check uniqueness excluding self
        if Category.objects.filter(name__iexact=name).exclude(id=category_id).exists():
            return Response({'error': 'conflict', 'message': 'A category with this name already exists.'}, status=409)
        if Category.objects.filter(slug=slug).exclude(id=category_id).exists():
            return Response({'error': 'conflict', 'message': 'A category with this slug already exists.'}, status=409)

        category.name          = name
        category.slug          = slug
        category.icon          = data.get('icon', '').strip()
        category.display_order = int(data.get('display_order', 0))
        category.is_active     = bool(data.get('is_active', True))
        category.save()
        return Response(CategorySerializer(category).data)

    def patch(self, request, category_id):
        category = self._get_category(category_id)
        if not category:
            return Response({'error': 'not_found'}, status=404)

        data = request.data
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return Response({'error': 'validation_error', 'message': 'name cannot be blank.'}, status=400)
            if Category.objects.filter(name__iexact=name).exclude(id=category_id).exists():
                return Response({'error': 'conflict', 'message': 'A category with this name already exists.'}, status=409)
            category.name = name
        if 'slug' in data:
            slug = data['slug'].strip()
            if Category.objects.filter(slug=slug).exclude(id=category_id).exists():
                return Response({'error': 'conflict', 'message': 'A category with this slug already exists.'}, status=409)
            category.slug = slug
        if 'icon' in data:
            category.icon = data['icon'].strip()
        if 'display_order' in data:
            category.display_order = int(data['display_order'])
        if 'is_active' in data:
            category.is_active = bool(data['is_active'])
        category.save()
        return Response(CategorySerializer(category).data)

    def delete(self, request, category_id):
        category = self._get_category(category_id)
        if not category:
            return Response({'error': 'not_found'}, status=404)
        category.delete()
        return Response(status=204)


class PublicCategoryListView(APIView):
    """GET /admin-panel/categories/public/ or /products/categories/ — active categories for vendors and customers."""
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.filter(is_active=True).order_by('display_order', 'name')
        serializer = CategorySerializer(categories, many=True)
        return Response({'count': categories.count(), 'results': serializer.data})


# ── Offer Template Management ──────────────────────────────────────────────────

class AdminOfferTemplateListCreateView(APIView):
    """GET/POST /admin-panel/offer-templates/ — list all or create an offer template (admin only)."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        templates = OfferTemplate.objects.all().order_by('display_order', 'name')
        serializer = OfferTemplateSerializer(templates, many=True)
        return Response({'count': templates.count(), 'results': serializer.data})

    def post(self, request):
        data = request.data
        name = data.get('name', '').strip()
        if not name:
            return Response({'error': 'validation_error', 'message': 'name is required.'}, status=400)

        is_default = bool(data.get('is_default', False))
        if is_default:
            OfferTemplate.objects.filter(is_default=True).update(is_default=False)

        template = OfferTemplate.objects.create(
            name                 = name,
            description_template = data.get('description_template', '').strip(),
            default_discount_pct = data.get('default_discount_pct') or None,
            badge_text           = data.get('badge_text', '').strip(),
            emoji                = data.get('emoji', '').strip(),
            image_url            = data.get('image_url', '').strip(),
            is_active            = bool(data.get('is_active', True)),
            is_default           = is_default,
            display_order        = int(data.get('display_order', 0)),
            created_by           = request.user,
        )
        return Response(OfferTemplateSerializer(template).data, status=201)


class AdminOfferTemplateDetailView(APIView):
    """PUT/PATCH/DELETE /admin-panel/offer-templates/<template_id>/"""
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_template(self, template_id):
        try:
            return OfferTemplate.objects.get(id=template_id)
        except OfferTemplate.DoesNotExist:
            return None

    def put(self, request, template_id):
        template = self._get_template(template_id)
        if not template:
            return Response({'error': 'not_found'}, status=404)

        data = request.data
        name = data.get('name', '').strip()
        if not name:
            return Response({'error': 'validation_error', 'message': 'name is required.'}, status=400)

        is_default = bool(data.get('is_default', False))
        if is_default and not template.is_default:
            OfferTemplate.objects.filter(is_default=True).exclude(id=template_id).update(is_default=False)

        template.name                 = name
        template.description_template = data.get('description_template', '').strip()
        template.default_discount_pct = data.get('default_discount_pct') or None
        template.badge_text           = data.get('badge_text', '').strip()
        template.emoji                = data.get('emoji', '').strip()
        template.image_url            = data.get('image_url', '').strip()
        template.is_active            = bool(data.get('is_active', True))
        template.is_default           = is_default
        template.display_order        = int(data.get('display_order', 0))
        template.save()
        return Response(OfferTemplateSerializer(template).data)

    def patch(self, request, template_id):
        template = self._get_template(template_id)
        if not template:
            return Response({'error': 'not_found'}, status=404)

        data = request.data
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return Response({'error': 'validation_error', 'message': 'name cannot be blank.'}, status=400)
            template.name = name
        if 'description_template' in data:
            template.description_template = data['description_template'].strip()
        if 'default_discount_pct' in data:
            template.default_discount_pct = data['default_discount_pct'] or None
        if 'badge_text' in data:
            template.badge_text = data['badge_text'].strip()
        if 'emoji' in data:
            template.emoji = data['emoji'].strip()
        if 'image_url' in data:
            template.image_url = data['image_url'].strip()
        if 'is_active' in data:
            template.is_active = bool(data['is_active'])
        if 'is_default' in data:
            new_is_default = bool(data['is_default'])
            if new_is_default and not template.is_default:
                OfferTemplate.objects.filter(is_default=True).exclude(id=template_id).update(is_default=False)
            template.is_default = new_is_default
        if 'display_order' in data:
            template.display_order = int(data['display_order'])
        template.save()
        return Response(OfferTemplateSerializer(template).data)

    def delete(self, request, template_id):
        template = self._get_template(template_id)
        if not template:
            return Response({'error': 'not_found'}, status=404)
        template.delete()
        return Response(status=204)


class PublicOfferTemplateListView(APIView):
    """GET /admin-panel/offer-templates/public/ or /stores/offer-templates/ — active templates for vendors."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        templates = OfferTemplate.objects.filter(is_active=True).order_by('-is_default', 'display_order', 'name')
        serializer = OfferTemplateSerializer(templates, many=True)
        return Response({'count': templates.count(), 'results': serializer.data})


# ── Helpers ────────────────────────────────────────────────────────────────────

def _log_action(admin, action: str, target_type: str, target_id: str,
                target_label: str, detail: str = '') -> None:
    try:
        AdminActivityLog.objects.create(
            admin=admin, action=action,
            target_type=target_type, target_id=target_id,
            target_label=target_label, detail=detail,
        )
    except Exception:
        pass  # activity log must never crash the main request


def _video_to_dict(v: Video) -> dict:
    return {
        'id':            str(v.id),
        'title':         v.title,
        'status':        v.status,
        'thumbnail_url': v.thumbnail_url,
        'video_url':     v.video_url,
        'view_count':    v.view_count,
        'like_count':    v.like_count,
        'created_at':    v.created_at.isoformat() if hasattr(v, 'created_at') and v.created_at else '',
    }


def _banner_to_dict(b: PromoBanner) -> dict:
    return {
        'id':            str(b.id),
        'title':         b.title,
        'subtitle':      b.subtitle,
        'badge_text':    b.badge_text,
        'image_url':     b.image_url,
        'link_type':     b.link_type,
        'link_value':    b.link_value,
        'display_order': b.display_order,
        'is_active':     b.is_active,
        'is_paid':       b.is_paid,
        'starts_at':     b.starts_at.isoformat() if b.starts_at else None,
        'ends_at':       b.ends_at.isoformat()   if b.ends_at   else None,
        'created_at':    b.created_at.isoformat(),
    }


def _admin_user_dict(u: User) -> dict:
    return {
        'id':                   str(u.id),
        'phone_number':         u.phone_number,
        'full_name':            u.full_name,
        'profile_id':           u.profile_id,
        'role':                 u.role,
        'is_active':            u.is_active,
        'admin_assigned_city':  u.admin_assigned_city,
        'created_at':           u.created_at.isoformat(),
    }
