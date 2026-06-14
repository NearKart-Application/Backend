"""
NearKart — Admin Panel Views
"""
import logging
from decimal import Decimal, InvalidOperation
from django.db.models import Count, Sum, Q
from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import serializers as s
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


def _in_scope(user, locality: str) -> bool:
    """True if master admin, or if the locality matches any of the admin's cities."""
    cities = _city_scope(user)
    if not cities:
        return True
    locality = (locality or '').lower()
    return any(c.lower() in locality for c in cities)


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
        cities = _city_scope(request.user)

        store_qs = Store.objects.all()
        if cities:
            store_qs = store_qs.filter(_city_q(cities, 'locality', 'address'))

        store_ids = store_qs.values_list('id', flat=True)

        store_counts = store_qs.aggregate(
            total    = Count('id'),
            active   = Count('id', filter=Q(is_active=True)),
            verified = Count('id', filter=Q(is_verified=True)),
            open     = Count('id', filter=Q(is_open=True)),
        )

        vendor_qs = User.objects.filter(role='vendor', stores__id__in=store_ids).distinct()
        if cities:
            customer_qs  = User.objects.filter(role='customer').filter(_city_q(cities, 'location_city')).distinct()
            user_total   = vendor_qs.count() + customer_qs.count()
            user_active  = vendor_qs.filter(is_active=True).count() + customer_qs.filter(is_active=True).count()
        else:
            user_counts  = User.objects.aggregate(
                total     = Count('id'),
                vendors   = Count('id', filter=Q(role='vendor')),
                customers = Count('id', filter=Q(role='customer')),
                active    = Count('id', filter=Q(is_active=True)),
            )
            user_total   = user_counts['total']
            user_active  = user_counts['active']
            customer_qs  = User.objects.filter(role='customer')

        video_qs = Video.objects.filter(store_id__in=store_ids)
        video_counts = video_qs.aggregate(
            total      = Count('id'),
            ready      = Count('id', filter=Q(status='ready')),
            total_views= Sum('view_count'),
            total_likes= Sum('like_count'),
        )

        product_count = Product.objects.filter(status='active', store_id__in=store_ids).count()
        pending_website_requests = WebsiteRequest.objects.filter(
            status='pending', store_id__in=store_ids
        ).count()

        revenue = Transaction.objects.filter(
            type='subscription', store_id__in=store_ids
        ).aggregate(total=Sum('amount'))['total'] or 0

        topup_total = Transaction.objects.filter(
            type='topup', store_id__in=store_ids
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'users': {
                'total':     user_total,
                'vendors':   vendor_qs.count(),
                'customers': customer_qs.count(),
                'active':    user_active,
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

        if not _in_scope(request.user, f'{store.locality} {store.address}'):
            return Response({'error': 'forbidden', 'message': 'Store is outside your assigned city.'}, status=403)

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
            city_vendors   = _city_q(cities, 'stores__locality', 'stores__address') & Q(role='vendor')
            city_customers = _city_q(cities, 'location_city') & Q(role='customer')
            qs = qs.filter(city_vendors | city_customers).distinct()

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
            user = User.objects.select_related('store').get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'User not found.'}, status=404)

        if user.id == request.user.id:
            return Response({'error': 'forbidden', 'message': 'Cannot deactivate your own account.'}, status=400)

        cities = _city_scope(request.user)
        if cities:
            user_locality = ''
            if user.role == 'vendor':
                try:
                    user_locality = user.store.locality or user.store.address
                except Exception:
                    pass
            else:
                user_locality = user.location_city or ''
            if not _in_scope(request.user, user_locality):
                return Response({'error': 'forbidden', 'message': 'User is outside your assigned city.'}, status=403)

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
        city = (request.query_params.get('city') or '').strip()
        banners = PromoBanner.objects.filter(
            is_active=True,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now)
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=now)
        ).order_by('display_order', '-created_at')

        if city:
            banners = banners.filter(Q(target_city='') | Q(target_city__iexact=city))

        data = [_banner_to_dict(b) for b in banners]
        return Response({'count': len(data), 'results': data})


# ── Admin Banner CRUD ──────────────────────────────────────────────────────────

class AdminBannerListCreateView(APIView):
    """GET/POST /admin-panel/banners/ — list all or create a banner."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        banners = PromoBanner.objects.all().order_by('display_order', '-created_at')
        cities = _city_scope(request.user)
        if cities:
            city_q = Q(target_city='')
            for c in cities:
                city_q |= Q(target_city__icontains=c)
            banners = banners.filter(city_q)
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
            target_city   = data.get('target_city', '').strip(),
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
        for field in ['title', 'subtitle', 'badge_text', 'image_url', 'link_type', 'link_value', 'target_city']:
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

        if not _in_scope(request.user, f'{product.store.locality} {product.store.address}'):
            return Response({'error': 'forbidden', 'message': 'Product is outside your assigned city.'}, status=403)

        allowed_fields = ['status', 'is_visible']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        serializer = AdminProductSerializer(product, data=data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()
        _log_action(request.user, 'update_product', 'product', str(product.id), product.name, str(data))
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

        cities = _city_scope(request.user)
        if cities:
            qs = qs.filter(_city_q(cities, 'store__locality', 'store__address'))

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

        if not _in_scope(request.user, f'{wr.store.locality} {wr.store.address}'):
            return Response({'error': 'forbidden', 'message': 'Request is outside your assigned city.'}, status=403)

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
            user = User.objects.select_related('store').get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'User not found.'}, status=404)

        if user.id == request.user.id:
            return Response({'error': 'forbidden', 'message': 'Cannot suspend your own account.'}, status=400)

        cities = _city_scope(request.user)
        if cities:
            user_locality = ''
            if user.role == 'vendor':
                try:
                    user_locality = user.store.locality or user.store.address
                except Exception:
                    pass
            else:
                user_locality = user.location_city or ''
            if not _in_scope(request.user, user_locality):
                return Response({'error': 'forbidden', 'message': 'User is outside your assigned city.'}, status=403)

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

        if not _in_scope(request.user, f'{store.locality} {store.address}'):
            return Response({'error': 'forbidden', 'message': 'Store is outside your assigned city.'}, status=403)

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

        if not _in_scope(request.user, f'{video.store.locality} {video.store.address}'):
            return Response({'error': 'forbidden', 'message': 'Video is outside your assigned city.'}, status=403)

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
        cities = _city_scope(request.user)
        log_qs = AdminActivityLog.objects.select_related('admin').order_by('-created_at')
        if cities:
            # City admins see only their own actions
            log_qs = log_qs.filter(admin=request.user)
        qs = log_qs[:100]
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
        'target_city':   b.target_city,
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


# ── Vendor Coupon Management ─────────────────────────────────────────────────


import random
import string

from apps.billing.models import Coupon, Plan as BillingPlan, CouponRedemption
from apps.notifications.services import NotificationService


def _generate_coupon_code(store_name: str) -> str:
    """Auto-generate: NS-{STORENAME_6CHARS}-{RANDOM6}"""
    name_part   = ''.join(c for c in store_name.upper() if c.isalnum())[:6].ljust(6, 'X')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f'NS-{name_part}-{random_part}'


def _coupon_dict(c: Coupon, include_redemptions: bool = False) -> dict:
    plans = list(c.applicable_plans.values('name', 'display_name'))
    data  = {
        'id':               str(c.id),
        'code':             c.code,
        'discount_percent': c.discount_percent,
        'plans':            plans,
        'max_uses':         c.max_uses,
        'used_count':       c.used_count,
        'expires_at':       c.expires_at.isoformat() if c.expires_at else None,
        'is_active':        c.is_active,
        'is_vendor_specific': c.is_vendor_specific,
        'target_store':     {
            'id':   str(c.target_store.id),
            'name': c.target_store.name,
        } if c.target_store else None,
        'created_by': {
            'id':        str(c.created_by.id),
            'full_name': c.created_by.full_name,
            'role':      c.created_by.role,
        } if c.created_by else None,
        'created_at': c.created_at.isoformat(),
        'status':     'availed' if c.used_count > 0 and c.max_uses == 1 else
                      ('expired' if (c.expires_at and c.expires_at < timezone.now()) or not c.is_active else 'active'),
    }
    if include_redemptions:
        redemptions = []
        for r in c.redemptions.select_related('store', 'subscription').all():
            redemptions.append({
                'store':          {'id': str(r.store.id), 'name': r.store.name},
                'plan_name':      r.plan_name,
                'plan_display':   r.plan_display,
                'original_price': str(r.original_price),
                'discount_given': str(r.discount_given),
                'price_paid':     str(r.price_paid),
                'redeemed_at':    r.redeemed_at.isoformat(),
            })
        data['redemptions'] = redemptions
    return data


class AdminCouponListCreateView(APIView):
    """
    GET  /admin-panel/coupons/  — list all vendor-specific coupons
    POST /admin-panel/coupons/  — create a new vendor-specific coupon
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=['Admin Panel'],
        summary='List vendor-specific coupons (admin)',
        parameters=[
            OpenApiParameter('status', str, description='Filter: active | availed | expired'),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        cities = _city_scope(request.user)
        qs     = Coupon.objects.filter(
            target_store__isnull=False
        ).select_related(
            'target_store', 'created_by'
        ).prefetch_related('applicable_plans').order_by('-created_at')

        if cities:
            qs = qs.filter(_city_q(cities, 'target_store__locality', 'target_store__address'))

        status_filter = request.query_params.get('status', '').lower()
        now = timezone.now()
        if status_filter == 'active':
            qs = qs.filter(is_active=True).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=now)
            ).filter(Q(max_uses=0) | Q(used_count__lt=1))
        elif status_filter == 'availed':
            qs = qs.filter(used_count__gte=1, max_uses=1)
        elif status_filter == 'expired':
            qs = qs.filter(Q(is_active=False) | Q(expires_at__lte=now))

        return Response([_coupon_dict(c) for c in qs])

    @extend_schema(
        tags=['Admin Panel'],
        summary='Create a vendor-specific coupon (admin)',
        request=inline_serializer('CreateVendorCouponRequest', fields={
            'store_id':         s.UUIDField(help_text='Target store ID'),
            'plan_name':        s.CharField(help_text='Plan slug: basic | premium (or empty for all)'),
            'discount_percent': s.IntegerField(help_text='Discount 1-100; 100 = free'),
            'expires_at':       s.DateTimeField(required=False, help_text='Optional expiry datetime'),
        }),
        responses={201: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        store_id         = (request.data.get('store_id')         or '').strip()
        plan_name        = (request.data.get('plan_name')         or '').strip().lower()
        discount_percent = request.data.get('discount_percent', 100)
        expires_at_raw   = request.data.get('expires_at')

        if not store_id:
            return Response({'error': 'validation_error', 'message': 'store_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            discount_percent = int(discount_percent)
            if not (1 <= discount_percent <= 100):
                raise ValueError()
        except (ValueError, TypeError):
            return Response({'error': 'validation_error', 'message': 'discount_percent must be 1–100.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_store = Store.objects.get(id=store_id)
        except (Store.DoesNotExist, Exception):
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not _in_scope(request.user, f'{target_store.locality} {target_store.address}'):
            return Response({'error': 'forbidden', 'message': 'Store is outside your assigned city.'}, status=status.HTTP_403_FORBIDDEN)

        plan_obj = None
        if plan_name:
            try:
                plan_obj = BillingPlan.objects.get(name=plan_name, is_active=True)
            except BillingPlan.DoesNotExist:
                return Response({'error': 'not_found', 'message': f'Plan "{plan_name}" not found.'}, status=status.HTTP_404_NOT_FOUND)

        expires_at = None
        if expires_at_raw:
            from django.utils.dateparse import parse_datetime
            expires_at = parse_datetime(str(expires_at_raw))
            if expires_at is None:
                return Response({'error': 'validation_error', 'message': 'Invalid expires_at format.'}, status=status.HTTP_400_BAD_REQUEST)

        code = _generate_coupon_code(target_store.name)
        coupon = Coupon.objects.create(
            code=code,
            discount_percent=discount_percent,
            max_uses=1,          # single-use vendor coupon
            target_store=target_store,
            created_by=request.user,
            expires_at=expires_at,
            is_active=True,
        )
        if plan_obj:
            coupon.applicable_plans.set([plan_obj])

        # Send push notification to vendor
        plan_display = plan_obj.display_name if plan_obj else 'Any Plan'
        try:
            NotificationService.notify_vendor_coupon(
                target_store.owner, plan_display, discount_percent, code,
            )
        except Exception as exc:
            logger.warning('Failed to send vendor coupon notification: %s', exc)

        return Response(_coupon_dict(coupon), status=status.HTTP_201_CREATED)


class AdminCouponDetailView(APIView):
    """
    GET    /admin-panel/coupons/{id}/ — full detail with redemption audit trail
    DELETE /admin-panel/coupons/{id}/ — deactivate (only if not yet availed)
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_coupon(self, coupon_id, user):
        try:
            coupon = Coupon.objects.select_related(
                'target_store', 'created_by'
            ).prefetch_related('applicable_plans', 'redemptions__store').get(
                id=coupon_id,
                target_store__isnull=False,
            )
        except (Coupon.DoesNotExist, Exception):
            return None

        cities = _city_scope(user)
        if cities and coupon.target_store:
            store_locality = f'{coupon.target_store.locality} {coupon.target_store.address}'
            if not _in_scope(user, store_locality):
                return None
        return coupon

    @extend_schema(
        tags=['Admin Panel'],
        summary='Vendor coupon detail with audit trail (admin)',
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, coupon_id):
        coupon = self._get_coupon(coupon_id, request.user)
        if not coupon:
            return Response({'error': 'not_found', 'message': 'Coupon not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_coupon_dict(coupon, include_redemptions=True))

    @extend_schema(
        tags=['Admin Panel'],
        summary='Deactivate a vendor coupon (admin) — only if not yet used',
        responses={200: OpenApiTypes.OBJECT},
    )
    def delete(self, request, coupon_id):
        coupon = self._get_coupon(coupon_id, request.user)
        if not coupon:
            return Response({'error': 'not_found', 'message': 'Coupon not found.'}, status=status.HTTP_404_NOT_FOUND)
        if coupon.used_count > 0:
            return Response({'error': 'already_used', 'message': 'This coupon has already been redeemed and cannot be deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        coupon.is_active = False
        coupon.save(update_fields=['is_active'])
        return Response({'message': 'Coupon deactivated.'})


class AdminVendorSearchView(APIView):
    """GET /admin-panel/vendors/search/?q=name — search vendors by store name/phone for coupon targeting."""
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=['Admin Panel'],
        summary='Search vendors/stores for coupon targeting (admin)',
        parameters=[
            OpenApiParameter('q', str, description='Search by store name or owner phone'),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        q      = (request.query_params.get('q') or '').strip()
        cities = _city_scope(request.user)

        qs = Store.objects.select_related('owner').filter(is_active=True)
        if cities:
            qs = qs.filter(_city_q(cities, 'locality', 'address'))
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(owner__phone_number__icontains=q) |
                Q(owner__full_name__icontains=q)
            )

        return Response([
            {
                'store_id':    str(s.id),
                'store_name':  s.name,
                'city':        s.locality or '',
                'owner_name':  s.owner.full_name,
                'owner_phone': s.owner.phone_number,
                'is_verified': s.is_verified,
            }
            for s in qs[:20]
        ])


# ── Plan Management (master admin only) ──────────────────────────────────────

def _plan_dict(plan):
    return {
        'name':          plan.name,
        'display_name':  plan.display_name,
        'price':         str(plan.price),
        'duration_days': plan.duration_days,
        'video_limit':   plan.video_limit,
        'product_limit': plan.product_limit,
        'store_track':   plan.store_track,
        'description':   plan.description,
        'is_active':     plan.is_active,
    }


class AdminPlanListView(APIView):
    """GET /admin-panel/plans/ — list all plans (master admin only).
       POST /admin-panel/plans/ — create a new plan (master admin only).
    """
    permission_classes = [IsMasterAdmin]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        plans = BillingPlan.objects.all().order_by('price')
        return Response([_plan_dict(p) for p in plans])

    @extend_schema(
        request=inline_serializer('PlanCreateRequest', fields={
            'name':          s.CharField(help_text='Unique slug e.g. basic-service'),
            'display_name':  s.CharField(help_text='Human-readable name'),
            'price':         s.DecimalField(max_digits=8, decimal_places=2),
            'duration_days': s.IntegerField(required=False, help_text='Default 30'),
            'video_limit':   s.IntegerField(required=False, help_text='0 = unlimited'),
            'product_limit': s.IntegerField(required=False, help_text='0 = unlimited'),
            'store_track':   s.ChoiceField(choices=['both', 'product', 'service'],
                                           help_text='Which vendor type sees this plan'),
            'description':   s.CharField(required=False),
            'is_active':     s.BooleanField(required=False),
        }),
        responses={201: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        name = (request.data.get('name') or '').strip().lower()
        display_name = (request.data.get('display_name') or '').strip()
        price = request.data.get('price')
        store_track = (request.data.get('store_track') or 'both').strip().lower()

        if not name or not display_name or price is None:
            return Response(
                {'error': 'validation_error', 'message': 'name, display_name, and price are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if BillingPlan.objects.filter(name=name).exists():
            return Response(
                {'error': 'duplicate', 'message': f'Plan "{name}" already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if store_track not in ('both', 'product', 'service'):
            return Response(
                {'error': 'validation_error', 'message': 'store_track must be both, product, or service.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan = BillingPlan.objects.create(
            name          = name,
            display_name  = display_name,
            price         = price,
            duration_days = int(request.data.get('duration_days', 30)),
            video_limit   = int(request.data.get('video_limit', 3)),
            product_limit = int(request.data.get('product_limit', 10)),
            store_track   = store_track,
            description   = request.data.get('description', ''),
            is_active     = request.data.get('is_active', True),
        )

        AdminActivityLog.objects.create(
            admin=request.user,
            action='create_plan',
            target_type='plan',
            target_id=plan.name,
            detail=f'Created plan "{plan.display_name}" (track={store_track}, price=₹{plan.price})',
        )

        return Response(_plan_dict(plan), status=status.HTTP_201_CREATED)


class AdminPlanDetailView(APIView):
    """PATCH /admin-panel/plans/{slug}/ — update plan fields (master admin only)."""
    permission_classes = [IsMasterAdmin]

    EDITABLE = {'display_name', 'price', 'duration_days', 'video_limit', 'product_limit',
                'store_track', 'description', 'is_active'}

    @extend_schema(
        request=inline_serializer('PlanUpdateRequest', fields={
            'display_name':  s.CharField(required=False),
            'price':         s.DecimalField(max_digits=8, decimal_places=2, required=False),
            'duration_days': s.IntegerField(required=False),
            'video_limit':   s.IntegerField(required=False, help_text='0 = unlimited'),
            'product_limit': s.IntegerField(required=False, help_text='0 = unlimited'),
            'store_track':   s.ChoiceField(choices=['both', 'product', 'service'], required=False),
            'description':   s.CharField(required=False),
            'is_active':     s.BooleanField(required=False),
        }),
        responses={200: OpenApiTypes.OBJECT},
    )
    def patch(self, request, slug):
        try:
            plan = BillingPlan.objects.get(name=slug)
        except BillingPlan.DoesNotExist:
            return Response({'error': 'not_found', 'message': f'Plan "{slug}" not found.'}, status=status.HTTP_404_NOT_FOUND)

        if 'store_track' in request.data and request.data['store_track'] not in ('both', 'product', 'service'):
            return Response(
                {'error': 'validation_error', 'message': 'store_track must be both, product, or service.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = []
        for field in self.EDITABLE:
            if field in request.data:
                setattr(plan, field, request.data[field])
                updated.append(field)

        if not updated:
            return Response({'error': 'no_fields', 'message': 'No valid fields provided.'}, status=status.HTTP_400_BAD_REQUEST)

        plan.save(update_fields=updated)

        AdminActivityLog.objects.create(
            admin=request.user,
            action='update_plan',
            target_type='plan',
            target_id=plan.name,
            detail=f'Updated plan "{plan.display_name}": {", ".join(updated)}',
        )

        return Response(_plan_dict(plan))


# ── Referral Config Management ────────────────────────────────────────────────

from apps.billing.models import ReferralConfig


def _referral_config_dict(cfg: ReferralConfig) -> dict:
    return {
        'id':                  str(cfg.id),
        'city':                cfg.city,
        'vendor_reward':       str(cfg.vendor_reward),
        'customer_reward':     str(cfg.customer_reward),
        'vendor_reward_min':   str(cfg.vendor_reward_min),
        'vendor_reward_max':   str(cfg.vendor_reward_max),
        'customer_reward_min': str(cfg.customer_reward_min),
        'customer_reward_max': str(cfg.customer_reward_max),
    }


class AdminReferralConfigListView(APIView):
    """
    GET  /admin-panel/referral-config/  — list configs (city-scoped for city admin)
    POST /admin-panel/referral-config/  — create city config
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        cities = _city_scope(request.user)
        if cities:
            qs = ReferralConfig.objects.filter(Q(city='') | Q(city__in=cities))
        else:
            qs = ReferralConfig.objects.all()
        return Response([_referral_config_dict(c) for c in qs.order_by('city')])

    def post(self, request):
        city = (request.data.get('city') or '').strip()
        if not city and request.user.role != 'master_admin':
            return Response(
                {'error': 'forbidden', 'message': 'Only master admin can edit the global config.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        cities = _city_scope(request.user)
        if cities and city not in cities:
            return Response(
                {'error': 'forbidden', 'message': 'You can only manage your assigned cities.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if ReferralConfig.objects.filter(city__iexact=city).exists():
            return Response(
                {'error': 'conflict', 'message': f'Config for "{city or "global"}" already exists.'},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            global_cfg = ReferralConfig.objects.get(city='')
        except ReferralConfig.DoesNotExist:
            global_cfg = None
        cfg = ReferralConfig.objects.create(
            city=city,
            vendor_reward=Decimal(str(request.data.get('vendor_reward', 50))),
            customer_reward=Decimal(str(request.data.get('customer_reward', 20))),
            vendor_reward_min=global_cfg.vendor_reward_min if global_cfg else Decimal('10'),
            vendor_reward_max=global_cfg.vendor_reward_max if global_cfg else Decimal('200'),
            customer_reward_min=global_cfg.customer_reward_min if global_cfg else Decimal('10'),
            customer_reward_max=global_cfg.customer_reward_max if global_cfg else Decimal('200'),
        )
        return Response(_referral_config_dict(cfg), status=status.HTTP_201_CREATED)


class AdminReferralConfigDetailView(APIView):
    """
    GET   /admin-panel/referral-config/<config_id>/  — get config
    PATCH /admin-panel/referral-config/<config_id>/  — update (range enforced for city admin)
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get(self, config_id):
        try:
            return ReferralConfig.objects.get(id=config_id)
        except ReferralConfig.DoesNotExist:
            return None

    def get(self, request, config_id):
        cfg = self._get(config_id)
        if not cfg:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_referral_config_dict(cfg))

    def patch(self, request, config_id):
        cfg = self._get(config_id)
        if not cfg:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

        cities = _city_scope(request.user)
        if cities and cfg.city not in cities:
            return Response({'error': 'forbidden', 'message': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

        is_master = request.user.role == 'master_admin'
        try:
            vendor_reward   = Decimal(str(request.data['vendor_reward']))   if 'vendor_reward'   in request.data else None
            customer_reward = Decimal(str(request.data['customer_reward'])) if 'customer_reward' in request.data else None
        except (InvalidOperation, ValueError):
            return Response({'error': 'validation_error', 'message': 'Invalid reward amount.'}, status=status.HTTP_400_BAD_REQUEST)

        if not is_master:
            if vendor_reward is not None and not (cfg.vendor_reward_min <= vendor_reward <= cfg.vendor_reward_max):
                return Response({
                    'error':   'out_of_range',
                    'message': f'Vendor reward must be ₹{cfg.vendor_reward_min}–₹{cfg.vendor_reward_max}.',
                }, status=status.HTTP_400_BAD_REQUEST)
            if customer_reward is not None and not (cfg.customer_reward_min <= customer_reward <= cfg.customer_reward_max):
                return Response({
                    'error':   'out_of_range',
                    'message': f'Customer reward must be ₹{cfg.customer_reward_min}–₹{cfg.customer_reward_max}.',
                }, status=status.HTTP_400_BAD_REQUEST)

        if vendor_reward   is not None: cfg.vendor_reward   = vendor_reward
        if customer_reward is not None: cfg.customer_reward = customer_reward

        if is_master:
            for field in ('vendor_reward_min', 'vendor_reward_max', 'customer_reward_min', 'customer_reward_max'):
                if field in request.data:
                    try:
                        setattr(cfg, field, Decimal(str(request.data[field])))
                    except (InvalidOperation, ValueError):
                        pass

        cfg.save()
        return Response(_referral_config_dict(cfg))
