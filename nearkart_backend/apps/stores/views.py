"""
NearKart — Store Views
GET  /api/v1/stores/nearby/
GET  /api/v1/stores/<id>/
POST /api/v1/stores/
PUT  /api/v1/stores/<id>/
POST /api/v1/stores/<id>/follow/
POST /api/v1/stores/<id>/review/
GET  /api/v1/stores/<id>/qr-code/
PUT  /api/v1/stores/<id>/hours/
"""
import logging
import threading
from django.conf import settings
from django.db import models
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse, inline_serializer
import rest_framework.serializers as s

from core.logging import log_event
from core.permissions import IsVendor, IsStoreOwner
from core.utils.vendor_log import log_vendor_action
from core.utils.customer_log import log_customer_action
from core.utils.cache import CacheService
from apps.blacklist.services import BlacklistService
from django.utils import timezone as tz
from .models import Store, StoreHours, StoreOffer, StoreReview, Invoice, WebsiteRequest, StaffMember, StaffRole, BroadcastChannel, BroadcastPost, CustomerBlockedStore, ServiceCatalogue, StorePhoto, StoreQuestion
from .serializers import (
    StoreSerializer, StoreListSerializer, StoreReviewSerializer,
    StoreReviewListSerializer, StoreOfferSerializer,
    StoreHoursSerializer, StoreMobileDetailSerializer, VendorReplySerializer,
    InvoiceSerializer, StaffMemberSerializer, StoreFollowerSerializer,
    CustomerInvoiceSerializer, annotate_stores_with_subcategories,
    ServiceCatalogueSerializer, StorePhotoSerializer, StoreQuestionSerializer,
)
from .services import StoreService, QRService

logger = logging.getLogger(__name__)

_TAG = 'Stores'


def _dispatch_store_opened(follower_ids: list, store_name: str, store_id: str):
    """Fire-and-forget: notify followers a store opened (avoids blocking the API response)."""
    def _run():
        from apps.auth_app.models import User
        from apps.notifications.services import NotificationService
        followers = list(User.objects.filter(id__in=follower_ids))
        NotificationService.notify_store_opened(followers, store_name, store_id)
    threading.Thread(target=_run, daemon=True).start()


def _dispatch_new_offer(follower_ids: list, store_name: str, offer_label: str, store_id: str):
    """Fire-and-forget: notify followers about a new offer."""
    def _run():
        from apps.auth_app.models import User
        from apps.notifications.services import NotificationService
        followers = list(User.objects.filter(id__in=follower_ids))
        NotificationService.notify_new_offer(followers, store_name, offer_label, store_id)
    threading.Thread(target=_run, daemon=True).start()


class NearbyStoresView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Get nearby stores',
        description='Returns stores within radius sorted by distance. No auth required.',
        parameters=[
            OpenApiParameter('lat',      float,  description='Latitude',              required=True),
            OpenApiParameter('lng',      float,  description='Longitude',             required=True),
            OpenApiParameter('radius',   int,    description='Radius in km (1/2/3/5)', required=False),
            OpenApiParameter('category',   str, description='Filter by category',           required=False),
            OpenApiParameter('store_type', str, description='Filter by type: product/service/home', required=False),
        ],
        responses={200: StoreListSerializer(many=True)},
        auth=[],
    )
    def get(self, request):
        try:
            lat      = float(request.query_params['lat'])
            lng      = float(request.query_params['lng'])
            radius     = int(request.query_params.get('radius', 2))
            category   = request.query_params.get('category')
            store_type = request.query_params.get('store_type')
        except (KeyError, ValueError):
            return Response(
                {'error': 'validation_error', 'message': 'lat and lng are required numbers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stores = annotate_stores_with_subcategories(StoreService.get_nearby(lat, lng, radius_km=radius, category=category, store_type=store_type))
        data = StoreListSerializer(stores, many=True).data
        return Response({'count': len(data), 'next': None, 'previous': None, 'results': data})


class StoreDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=[_TAG], summary='Get store detail', responses={200: StoreSerializer}, auth=[])
    def get(self, request, store_id):
        key    = CacheService.store_detail_key(str(store_id))
        cached = CacheService.get(key)
        if cached:
            # Algorithm 5 — HyperLogLog: count unique visitors even on cache hits
            if request.user and request.user.is_authenticated:
                CacheService.record_store_visit(str(store_id), str(request.user.id))
            # Recompute per-user is_followed — not cached to avoid leaking user-specific state
            from .models import StoreFollow
            cached = dict(cached)
            cached['is_followed'] = (
                StoreFollow.objects.filter(store_id=store_id, user=request.user).exists()
                if (request.user and request.user.is_authenticated) else False
            )
            return Response(cached)
        try:
            from django.db.models import Count, Avg, Prefetch
            from .models import StoreHours, StorePhoto
            store = Store.objects.prefetch_related(
                Prefetch('hours', queryset=StoreHours.objects.all()),
                Prefetch('photos', queryset=StorePhoto.objects.order_by('order', 'created_at')[:12]),
                'followers',
            ).annotate(
                follower_count=Count('followers', distinct=True),
                avg_rating=Avg('reviews__rating'),
                review_count_ann=Count('reviews', distinct=True),
            ).get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = StoreMobileDetailSerializer(store, context={'request': request}).data
        # Strip user-specific field before caching so different callers don't get each other's state
        cache_data = {k: v for k, v in data.items() if k != 'is_followed'}
        CacheService.set(key, cache_data, timeout=CacheService.TTL_STORE_DETAIL)
        # Algorithm 5 — HyperLogLog unique visitor tracking
        if request.user and request.user.is_authenticated:
            CacheService.record_store_visit(str(store_id), str(request.user.id))
        log_customer_action(request, 'store_view', entity_type='store',
                            entity_id=str(store_id), entity_name=store.name,
                            meta={'category': store.category, 'locality': store.locality})
        return Response(data)


class SimilarStoresView(APIView):
    """GET /stores/<store_id>/similar/ — up to 5 stores in the same category within 5 km."""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Similar stores nearby',
        description='Returns up to 5 stores with the same category within 5 km, excluding the requested store.',
        responses={200: StoreListSerializer(many=True)},
        auth=[],
    )
    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=404)

        if not store.location:
            return Response({'results': [], 'count': 0})

        lat = store.location.y
        lng = store.location.x
        nearby = StoreService.get_nearby(lat, lng, radius_km=5, category=store.category)
        similar = annotate_stores_with_subcategories([s for s in nearby if str(s.id) != str(store_id)][:5])
        data = StoreListSerializer(similar, many=True).data
        return Response({'results': data, 'count': len(data)})


class StoreCreateView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Create store (vendor only)',
        request=StoreSerializer,
        responses={201: StoreSerializer},
        examples=[
            OpenApiExample(
                'Sample store (Chennai)',
                request_only=True,
                value={
                    'name': 'Ravi Fashion House',
                    'description': 'Latest collections in kurtas, sarees, and ethnic wear.',
                    'category': 'fashion',
                    'phone': '+919876543210',
                    'address': '12, MG Road, T Nagar, Chennai',
                    'latitude': 13.0827,
                    'longitude': 80.2707,
                    'is_open': True,
                },
            ),
        ],
    )
    def post(self, request):
        serializer = StoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = StoreService.create(request.user, serializer.validated_data)
        log_event('stores', action='store_created', store_id=str(store.id),
                  user_id=str(request.user.id), name=store.name, category=store.category)
        return Response(StoreSerializer(store).data, status=status.HTTP_201_CREATED)


class StoreUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsStoreOwner]

    @extend_schema(tags=[_TAG], summary='Update store (owner only)', request=StoreSerializer, responses={200: StoreSerializer})
    def put(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)
        serializer = StoreSerializer(store, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        was_open = store.is_open
        store = StoreService.update(store, serializer.validated_data)
        if not was_open and store.is_open:
            from apps.stores.models import StoreFollow
            follower_ids = list(StoreFollow.objects.filter(store=store).values_list('user_id', flat=True))
            _dispatch_store_opened(follower_ids, store.name, str(store.id))
            log_event('stores', action='store_opened', store_id=str(store.id),
                      user_id=str(request.user.id), name=store.name)
        elif was_open and not store.is_open:
            log_event('stores', action='store_closed', store_id=str(store.id),
                      user_id=str(request.user.id), name=store.name)
        else:
            log_event('stores', action='store_updated', store_id=str(store.id),
                      user_id=str(request.user.id))
        log_vendor_action(request, 'store_update', store=store, entity_type='store',
                          entity_id=str(store.id), entity_name=store.name,
                          meta={'fields': list(serializer.validated_data.keys()), 'is_open': store.is_open})
        return Response(StoreSerializer(store).data)


class StoreFollowView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Follow / unfollow store',
        request=None,
        responses={200: OpenApiResponse(
            response=inline_serializer('FollowResponse', fields={
                'followed': s.BooleanField(),
                'message': s.CharField(),
            })
        )},
    )
    def post(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.role == 'customer' and BlacklistService.is_blocked(store, request.user):
            return Response(
                {'error': 'blacklisted', 'message': 'You cannot follow this store.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        followed = StoreService.toggle_follow(request.user, store)
        msg = 'Following store.' if followed else 'Unfollowed store.'
        log_event('stores', action='store_followed' if followed else 'store_unfollowed',
                  store_id=str(store_id), user_id=str(request.user.id), store_name=store.name)
        log_event('customers', action='store_followed' if followed else 'store_unfollowed',
                  user_id=str(request.user.id), store_id=str(store_id))
        return Response({'followed': followed, 'message': msg})

    @extend_schema(tags=[_TAG], summary='Unfollow store', responses={200: None})
    def delete(self, request, store_id):
        """Mobile sends DELETE to explicitly unfollow — alias that always unfollows."""
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        from apps.stores.models import StoreFollow
        StoreFollow.objects.filter(user=request.user, store=store).delete()
        return Response({'followed': False, 'message': 'Unfollowed store.'})


class StoreFollowerListView(APIView):
    """
    GET /api/v1/stores/mine/followers/ — list the vendor's store followers.
    Returns name + NS code only; no phone or email exposed.
    """
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='List store followers')
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'results': [], 'count': 0})
        from apps.stores.models import StoreFollow
        qs = (
            StoreFollow.objects
            .filter(store=request.user.store)
            .select_related('user')
            .order_by('-created_at')
        )
        count = qs.count()
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 30)), 1), 50)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        start = (page - 1) * page_size
        ser = StoreFollowerSerializer(qs[start:start + page_size], many=True)
        return Response({'results': ser.data, 'count': count})


class StoreReviewView(APIView):
    """
    GET  /stores/<id>/reviews/ — list reviews (public, also accepted at /review/)
    POST /stores/<id>/reviews/ — add/update review (also accepted at /review/)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(tags=[_TAG], summary='List store reviews', responses={200: StoreReviewListSerializer(many=True)}, auth=[])
    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        key    = CacheService.store_reviews_key(str(store_id))
        cached = CacheService.get(key)
        if cached is not None:
            return Response(cached)
        reviews_qs = store.reviews.select_related('user').order_by('-created_at')
        total = reviews_qs.count()
        reviews = reviews_qs[:50]
        data = {'results': StoreReviewListSerializer(reviews, many=True).data, 'count': total}
        CacheService.set(key, data, timeout=CacheService.TTL_STORE_REVIEWS)
        return Response(data)

    @extend_schema(
        tags=[_TAG],
        summary='Add or update review',
        request=StoreReviewSerializer,
        responses={200: StoreReviewSerializer},
        examples=[
            OpenApiExample(
                'Five-star review',
                request_only=True,
                value={'rating': 5, 'comment': 'Great store, quality products and fast service!'},
            ),
            OpenApiExample(
                'Three-star review',
                request_only=True,
                value={'rating': 3, 'comment': 'Good products but delivery was slow.'},
            ),
        ],
    )
    def post(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.role == 'customer' and BlacklistService.is_blocked(store, request.user):
            return Response(
                {'error': 'blacklisted', 'message': 'You cannot review this store.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Gate: completed reservation OR invoice with customer's NS code
        from apps.reservations.models import Reservation, ReservationStatus
        has_reservation = Reservation.objects.filter(
            customer=request.user, store=store, status=ReservationStatus.COMPLETED,
        ).exists()
        ns_code = request.user.profile_id or ''
        has_invoice = (
            bool(ns_code) and
            Invoice.objects.filter(store=store, customer_ns_code=ns_code).exists()
        )
        if not (has_reservation or has_invoice):
            return Response(
                {'error': 'not_eligible',
                 'message': 'You can only review a store after a completed reservation or purchase there.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        is_verified = has_invoice
        serializer = StoreReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = StoreService.add_review(
            request.user, store,
            serializer.validated_data['rating'],
            serializer.validated_data.get('comment', ''),
            is_verified=is_verified,
        )
        CacheService.invalidate_store_reviews(str(store_id))
        # NOTE: notification is sent inside StoreService.add_review — do not duplicate here
        return Response(StoreReviewSerializer(review).data)


class StoreReviewEligibilityView(APIView):
    """
    GET /stores/<id>/review-eligibility/
    Returns whether the authenticated customer can review this store and
    which products (from their invoices at this store) they can review.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=[_TAG], summary='Check review eligibility for store + products')
    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)

        from apps.reservations.models import Reservation, ReservationStatus
        from apps.products.models import Product, ProductReview

        ns_code = request.user.profile_id or ''

        # Shop review eligibility
        has_reservation = Reservation.objects.filter(
            customer=request.user, store=store, status=ReservationStatus.COMPLETED,
        ).exists()
        has_invoice = (
            bool(ns_code) and
            Invoice.objects.filter(store=store, customer_ns_code=ns_code).exists()
        )
        can_review_shop = has_reservation or has_invoice
        has_shop_review = store.reviews.filter(user=request.user).exists()

        # Product review eligibility — scan all invoices for this customer at this store
        eligible_products = []
        if ns_code:
            invoices = list(Invoice.objects.filter(store=store, customer_ns_code=ns_code))
            reviewed_ids = set(
                ProductReview.objects.filter(reviewer=request.user)
                .values_list('product_id', flat=True)
            )
            # Collect unique product IDs first (with their first-seen invoice ID)
            pid_to_inv_id = {}
            for inv in invoices:
                for item in (inv.items or []):
                    pid_str = str(item.get('product_id', '')).strip()
                    if pid_str and pid_str not in pid_to_inv_id:
                        pid_to_inv_id[pid_str] = str(inv.id)

            # Single query to fetch all products instead of one per item
            products_map = {
                str(p.id): p
                for p in Product.objects.filter(id__in=pid_to_inv_id.keys())
            }
            for pid_str, inv_id in pid_to_inv_id.items():
                product = products_map.get(pid_str)
                if not product:
                    continue
                eligible_products.append({
                    'product_id':   str(product.id),
                    'product_name': product.name,
                    'invoice_id':   inv_id,
                    'has_reviewed': product.id in reviewed_ids,
                })

        return Response({
            'can_review_shop':  can_review_shop,
            'has_shop_review':  has_shop_review,
            'eligible_products': eligible_products,
        })


class StoreQRCodeView(APIView):
    permission_classes = [IsAuthenticated, IsStoreOwner]

    @extend_schema(
        tags=[_TAG],
        summary='Generate or get QR code',
        responses={200: OpenApiResponse(
            response=inline_serializer('QRResponse', fields={'qr_code_url': s.URLField()})
        )},
    )
    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)
        if not store.qr_code_url:
            QRService.generate_and_upload(store)
        return Response({'qr_code_url': store.qr_code_url})


class StoreHoursView(APIView):
    permission_classes = [IsAuthenticated, IsStoreOwner]

    @extend_schema(
        tags=[_TAG],
        summary='Get store hours',
        responses={200: StoreHoursSerializer(many=True)},
    )
    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)
        hours = StoreHours.objects.filter(store=store).order_by('day')
        return Response(StoreHoursSerializer(hours, many=True).data)

    @extend_schema(
        tags=[_TAG],
        summary='Set store hours (replaces all existing hours)',
        description=(
            'Send an array of up to 7 day entries. Each day: `day` (0=Mon…6=Sun), '
            '`open_time` (HH:MM), `close_time` (HH:MM), `is_closed` (bool). '
            'Replaces all existing hours — omitted days are deleted.'
        ),
        request=StoreHoursSerializer(many=True),
        responses={200: StoreHoursSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Weekday hours',
                request_only=True,
                value=[
                    {'day': 0, 'open_time': '09:00', 'close_time': '21:00', 'is_closed': False},
                    {'day': 1, 'open_time': '09:00', 'close_time': '21:00', 'is_closed': False},
                    {'day': 5, 'open_time': '10:00', 'close_time': '22:00', 'is_closed': False},
                    {'day': 6, 'open_time': '00:00', 'close_time': '00:00', 'is_closed': True},
                ],
            ),
        ],
    )
    def put(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)

        serializer = StoreHoursSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        days_seen = [entry['day'] for entry in serializer.validated_data]
        if len(days_seen) != len(set(days_seen)):
            return Response(
                {'error': 'validation_error', 'message': 'Duplicate day entries are not allowed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        StoreHours.objects.filter(store=store).delete()
        hours = StoreHours.objects.bulk_create([
            StoreHours(store=store, **entry)
            for entry in serializer.validated_data
        ])
        CacheService.delete(CacheService.store_detail_key(str(store.id)))
        log_vendor_action(request, 'store_hours_update', store=store, entity_type='store',
                          entity_id=str(store_id), entity_name=store.name,
                          meta={'days_set': len(hours)})
        return Response(StoreHoursSerializer(sorted(hours, key=lambda h: h.day), many=True).data)


class StorePhotoView(APIView):
    """GET  /stores/<id>/photos/   — public list of gallery photos
       POST /stores/<id>/photos/   — vendor adds a photo (image_url + optional caption)
       DELETE /stores/<id>/photos/<photo_id>/ — vendor deletes a photo"""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsStoreOwner()]

    def get(self, request, store_id):
        photos = StorePhoto.objects.filter(store_id=store_id).order_by('order', 'created_at')
        return Response(StorePhotoSerializer(photos, many=True).data)

    def post(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)
        serializer = StorePhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = serializer.save(store=store)
        CacheService.delete(CacheService.store_detail_key(str(store.id)))
        return Response(StorePhotoSerializer(photo).data, status=status.HTTP_201_CREATED)


class StorePhotoDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def delete(self, request, store_id, photo_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)
        StorePhoto.objects.filter(id=photo_id, store=store).delete()
        CacheService.delete(CacheService.store_detail_key(str(store.id)))
        return Response(status=status.HTTP_204_NO_CONTENT)


class StoreQAView(APIView):
    """GET  /stores/<id>/qa/   — public list of Q&A (answered questions first)
       POST /stores/<id>/qa/   — authenticated customer posts a question"""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, store_id):
        qs = StoreQuestion.objects.filter(store_id=store_id).select_related('user').order_by('-answered_at', '-created_at')[:20]
        from .serializers import StoreQuestionSerializer
        return Response(StoreQuestionSerializer(qs, many=True).data)

    def post(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = StoreQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(store=store, user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StoreQAAnswerView(APIView):
    """PATCH /stores/<id>/qa/<question_id>/ — vendor answers a question"""
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def patch(self, request, store_id, question_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)
        try:
            question = StoreQuestion.objects.get(id=question_id, store=store)
        except StoreQuestion.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        answer = request.data.get('answer', '').strip()
        if not answer:
            return Response({'error': 'Answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        question.answer = answer
        question.answered_at = timezone.now()
        question.save(update_fields=['answer', 'answered_at', 'updated_at'])
        from .serializers import StoreQuestionSerializer
        return Response(StoreQuestionSerializer(question).data)


class VendorReviewReplyView(APIView):
    """POST /api/v1/stores/<store_id>/reviews/<review_id>/reply/ — vendor replies to a review."""
    permission_classes = [IsAuthenticated, IsStoreOwner]

    @extend_schema(
        tags=[_TAG],
        summary='Reply to a customer review (store owner only)',
        request=VendorReplySerializer,
        responses={200: StoreReviewListSerializer},
        examples=[
            OpenApiExample(
                'Vendor reply',
                request_only=True,
                value={'reply': 'Thank you for your kind words! We look forward to seeing you again.'},
            ),
        ],
    )
    def post(self, request, store_id, review_id):
        try:
            store  = Store.objects.get(id=store_id)
            review = store.reviews.get(id=review_id)
        except (Store.DoesNotExist, StoreReview.DoesNotExist):
            return Response({'error': 'not_found', 'message': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)
        serializer = VendorReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from django.utils import timezone
        review.vendor_reply    = serializer.validated_data['reply']
        review.vendor_reply_at = timezone.now()
        review.save(update_fields=['vendor_reply', 'vendor_reply_at'])
        CacheService.invalidate_store_reviews(str(store_id))
        return Response(StoreReviewListSerializer(review).data)


class VendorReviewsListView(APIView):
    """GET /api/v1/stores/<store_id>/reviews/vendor/ — all reviews for vendor's store."""
    permission_classes = [IsAuthenticated, IsStoreOwner]

    @extend_schema(tags=[_TAG], summary='List all reviews for my store (vendor only)', responses={200: StoreReviewListSerializer(many=True)})
    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)
        reviews = store.reviews.select_related('user').order_by('-created_at')
        count     = reviews.count()
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 50)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        offset    = (page - 1) * page_size
        return Response({'results': StoreReviewListSerializer(reviews[offset:offset + page_size], many=True).data, 'count': count})


class MyReviewsView(APIView):
    """GET /api/v1/reviews/mine/ — all reviews written by the authenticated customer."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=[_TAG], summary='Get my reviews (customer)', responses={200: StoreReviewListSerializer(many=True)})
    def get(self, request):
        from .models import StoreReview
        reviews   = StoreReview.objects.filter(user=request.user).select_related('store').order_by('-created_at')
        count     = reviews.count()
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 50)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        offset    = (page - 1) * page_size
        data = []
        for r in reviews[offset:offset + page_size]:
            d = StoreReviewListSerializer(r).data
            d['store_id']   = str(r.store.id)
            d['store_name'] = r.store.name
            data.append(d)
        return Response({'results': data, 'count': count})



class StoreOfferView(APIView):
    """
    GET  /api/v1/stores/<id>/offers/ — list active offers (public)
    POST /api/v1/stores/<id>/offers/ — create offer (vendor/owner only)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsStoreOwner()]

    @extend_schema(tags=[_TAG], summary='List active offers for a store', responses={200: StoreOfferSerializer(many=True)}, auth=[])
    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        key    = CacheService.store_offers_key(str(store_id))
        cached = CacheService.get(key)
        if cached is not None:
            return Response(cached)
        from django.utils import timezone
        offers = store.offers.filter(is_active=True).filter(
            models.Q(valid_till__isnull=True) | models.Q(valid_till__gte=timezone.now().date())
        ).order_by('-created_at')
        data = {'results': StoreOfferSerializer(offers, many=True).data, 'count': offers.count()}
        CacheService.set(key, data, timeout=CacheService.TTL_STORE_OFFERS)
        return Response(data)

    @extend_schema(
        tags=[_TAG], summary='Create offer (store owner only)',
        request=StoreOfferSerializer, responses={201: StoreOfferSerializer},
        examples=[OpenApiExample('Festival offer', request_only=True, value={
            'title': 'Eid Special 🌙', 'description': '20% off on all kurtas this Eid.',
            'discount_pct': 20, 'valid_till': '2026-04-10',
        })],
    )
    def post(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)
        serializer = StoreOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = StoreOffer.objects.create(store=store, **serializer.validated_data)
        CacheService.delete(CacheService.store_detail_key(str(store.id)))
        CacheService.invalidate_store_offers(str(store_id))
        if store.location:
            CacheService.invalidate_store_caches(store.location.y, store.location.x)
        from apps.stores.models import StoreFollow
        follower_ids = list(StoreFollow.objects.filter(store=store).values_list('user_id', flat=True))
        if follower_ids:
            disc = f' — {offer.discount_pct}% off' if offer.discount_pct else ''
            _dispatch_new_offer(follower_ids, store.name, offer.title + disc, str(store.id))
        log_vendor_action(request, 'offer_create', store=store, entity_type='offer',
                          entity_id=str(offer.id), entity_name=offer.title,
                          meta={'discount_pct': offer.discount_pct, 'valid_till': str(offer.valid_till) if offer.valid_till else ''})
        return Response(StoreOfferSerializer(offer).data, status=status.HTTP_201_CREATED)


class StoreMyView(APIView):
    """GET /api/v1/stores/mine/ — return the authenticated vendor's own store."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='Get my store (vendor only)', responses={200: StoreSerializer})
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'error': 'not_found', 'message': 'You do not have a store yet.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(StoreSerializer(request.user.store).data)


class StoreVisitedView(APIView):
    """GET /api/v1/stores/visited/ — return stores the user follows (proxy for visit history)."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Get recently visited / followed stores',
        parameters=[OpenApiParameter('limit', int, description='Max results (default 5)', required=False)],
        responses={200: StoreListSerializer(many=True)},
    )
    def get(self, request):
        try:
            limit = max(int(request.query_params.get('limit', 5)), 1)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        from apps.stores.models import StoreFollow
        store_ids = StoreFollow.objects.filter(user=request.user)\
            .order_by('-created_at').values_list('store_id', flat=True)[:limit]
        stores = annotate_stores_with_subcategories(
            list(Store.objects.filter(id__in=store_ids, is_active=True).prefetch_related('offers', 'hours'))
        )
        return Response({'results': StoreListSerializer(stores, many=True).data, 'count': len(stores)})


class StoreOfferDeleteView(APIView):
    """DELETE /api/v1/stores/<store_id>/offers/<offer_id>/ — deactivate an offer."""
    permission_classes = [IsAuthenticated, IsStoreOwner]

    @extend_schema(tags=[_TAG], summary='Deactivate offer', responses={204: None})
    def delete(self, request, store_id, offer_id):
        try:
            store = Store.objects.get(id=store_id)
            offer = StoreOffer.objects.get(id=offer_id, store=store)
        except (Store.DoesNotExist, StoreOffer.DoesNotExist):
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, store)
        offer_title = offer.title
        offer.is_active = False
        offer.save(update_fields=['is_active'])
        CacheService.invalidate_store_offers(str(store_id))
        if store.location:
            CacheService.invalidate_store_caches(store.location.y, store.location.x)
        log_vendor_action(request, 'offer_delete', store=store, entity_type='offer',
                          entity_id=str(offer_id), entity_name=offer_title)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StoreStatsView(APIView):
    """GET /api/v1/stores/mine/stats/ — KPI summary for the vendor dashboard."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='Get my store stats (vendor only)')
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response({
                'store_name': '', 'store_address': '',
                'active_reservations': 0, 'total_products': 0, 'follower_count': 0,
            })
        store = request.user.store
        from apps.reservations.models import Reservation
        from apps.chat.models import Conversation
        from django.db.models import Sum
        from core.utils.cache import CacheService

        active_res = Reservation.objects.filter(
            store=store, status__in=['pending', 'confirmed']
        ).count()

        # Unique store views — sum HyperLogLog counts over last 30 days
        store_views = sum(CacheService.get_unique_visitors_range(str(store.id), days=30).values())

        # Unread chat conversations (vendor hasn't replied)
        inquiries_pending = Conversation.objects.filter(
            store=store, unread_count_vendor__gt=0
        ).count()

        # Active products where all variants are out of stock
        products_need_action = store.products.filter(status='active').annotate(
            total_stock=Sum('variants__stock_quantity')
        ).filter(total_stock=0).count()

        return Response({
            'store_name':            store.name,
            'store_address':         store.address,
            'store_slug':            store.slug or '',
            'active_reservations':   active_res,
            'total_products':        store.products.filter(status='active').count(),
            'follower_count':        store.followers.count(),
            'store_views':           store_views,
            'inquiries_pending':     inquiries_pending,
            'products_need_action':  products_need_action,
        })


class StoreInvoiceListCreateView(APIView):
    """
    GET  /api/v1/stores/mine/invoices/ — list vendor's invoices
    POST /api/v1/stores/mine/invoices/ — create an invoice
    """
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='List vendor invoices', responses={200: InvoiceSerializer(many=True)})
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'results': [], 'count': 0})
        invoices  = Invoice.objects.filter(store=request.user.store).order_by('-created_at')
        count     = invoices.count()
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 100)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        offset    = (page - 1) * page_size
        return Response({'results': InvoiceSerializer(invoices[offset:offset + page_size], many=True).data, 'count': count})

    @extend_schema(tags=[_TAG], summary='Create invoice', request=InvoiceSerializer, responses={201: InvoiceSerializer})
    def post(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'error': 'no_store'}, status=status.HTTP_400_BAD_REQUEST)
        ser = InvoiceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        items = ser.validated_data.get('items', [])
        try:
            subtotal = sum(float(i.get('price', 0)) * int(i.get('qty', 1)) for i in items)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_item', 'message': 'Item price and qty must be valid numbers.'}, status=400)
        discount_type  = ser.validated_data.get('discount_type') or ''
        discount_value = float(ser.validated_data.get('discount_value') or 0)
        if discount_type == 'amount':
            total = max(0.0, subtotal - discount_value)
        elif discount_type == 'percent':
            total = subtotal * max(0.0, (1 - discount_value / 100))
        else:
            total = subtotal

        # Stock pre-check: validate all linked products have enough stock before saving
        from apps.products.models import Product
        from django.db.models import Sum
        stock_errors = []
        for item in items:
            product_id = str(item.get('product_id', '')).strip()
            if not product_id:
                continue
            qty = max(1, int(item.get('qty', 1)))
            try:
                product = Product.objects.get(id=product_id, store=request.user.store)
                available = product.variants.aggregate(total=Sum('stock_quantity'))['total'] or 0
                if qty > available:
                    stock_errors.append(
                        f'"{product.name}": requested {qty}, only {available} in stock'
                    )
            except Product.DoesNotExist:
                pass
        if stock_errors:
            return Response(
                {'error': 'insufficient_stock', 'message': 'Not enough stock for: ' + '; '.join(stock_errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If vendor provided a customer NS code, auto-fill name and mark as sent
        ns_code = ser.validated_data.get('customer_ns_code', '').strip().upper()
        customer_user = None
        if ns_code:
            from apps.auth_app.models import User
            try:
                customer_user = User.objects.get(profile_id=ns_code)
                ser.validated_data['customer_name'] = customer_user.full_name or ser.validated_data.get('customer_name', '')
            except User.DoesNotExist:
                pass

        from django.db import transaction as db_transaction
        with db_transaction.atomic():
            invoice = ser.save(
                store=request.user.store,
                total=total,
                is_sent=customer_user is not None,
            )

            # Deduct inventory stock for each item linked to a product
            from apps.products.inventory_service import InventoryService
            from apps.products.models import StockMovementLog as _SML
            for item in items:
                product_id = str(item.get('product_id', '')).strip()
                if product_id:
                    qty = max(1, int(item.get('qty', 1)))
                    variant_id = str(item.get('variant_id', '')).strip() or None
                    InventoryService.deduct_for_invoice(
                        product_id=product_id,
                        qty=qty,
                        changed_by=request.user,
                        invoice_id=str(invoice.id),
                        store=request.user.store,
                        variant_id=variant_id,
                    )

            # Write back the exact variant_id that was deducted into each item's JSON.
            # The Returns flow uses this to auto-resolve which variant to restock —
            # without it the vendor would have to re-pick size/colour, risking a mismatch.
            updated_items = [dict(it) for it in items]
            invoice_note  = f'invoice:{invoice.id}'
            for it in updated_items:
                pid = str(it.get('product_id', '')).strip()
                if not pid or it.get('variant_id'):
                    continue  # manual item or frontend already supplied variant_id
                log = (
                    _SML.objects
                    .filter(variant__product_id=pid, note=invoice_note)
                    .select_related('variant')
                    .first()
                )
                if log and log.variant_id:
                    it['variant_id'] = str(log.variant_id)
            invoice.items = updated_items
            invoice.save(update_fields=['items'])

        if customer_user is not None:
            from apps.notifications.services import NotificationService
            store_name = request.user.store.name
            threading.Thread(
                target=NotificationService.notify_invoice_received,
                args=(customer_user, store_name, str(invoice.id), str(int(total))),
                daemon=True,
            ).start()

        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceReturnView(APIView):
    """
    POST /stores/mine/invoices/<id>/return/
    Process a customer return for one or more items in an invoice.

    Atomically:
      1. Validates return quantities (return_qty ≤ qty − returned_qty per item)
      2. Increments returned_qty in the invoice items JSON
      3. Adds stock back to the correct variant (reason = return_from_customer)
      4. Creates a StockMovementLog entry with the correct reason and note

    Request body:
        {
          "items": [
            {"item_index": 0, "return_qty": 1, "reason": "Defective / damaged"},
            {"item_index": 2, "return_qty": 2, "reason": "Changed mind"}
          ]
        }
    """
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(id=invoice_id, store=request.user.store)
        except Invoice.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

        return_items = request.data.get('items', [])
        if not isinstance(return_items, list) or not return_items:
            return Response(
                {'error': 'no_items', 'message': 'Provide a non-empty items list.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.inventory.services import InventoryService
        from apps.inventory.models import StockMovementReason
        from apps.products.models import ProductVariant
        from django.db import transaction as db_transaction

        invoice_items  = [dict(it) for it in (invoice.items or [])]
        invoice_label  = f'NS-{str(invoice.id)[-8:].upper()}'
        processed      = 0
        restocked      = 0
        errors         = []

        with db_transaction.atomic():
            for ri in return_items:
                idx = ri.get('item_index')
                try:
                    return_qty = max(1, int(ri.get('return_qty', 1)))
                except (TypeError, ValueError):
                    errors.append(f'item_index {idx}: invalid return_qty')
                    continue

                reason_label = str(ri.get('reason', 'Customer return'))[:200]

                if not isinstance(idx, int) or idx < 0 or idx >= len(invoice_items):
                    errors.append(f'Invalid item_index {idx}')
                    continue

                inv_item         = invoice_items[idx]
                already_returned = int(inv_item.get('returned_qty', 0))
                total_qty        = int(inv_item.get('qty', 0))
                max_returnable   = total_qty - already_returned

                if max_returnable <= 0:
                    errors.append(f'"{inv_item.get("name", idx)}" is already fully returned')
                    continue

                if return_qty > max_returnable:
                    errors.append(
                        f'"{inv_item.get("name", idx)}": return_qty {return_qty} exceeds remaining {max_returnable}'
                    )
                    continue

                # Update returned_qty in invoice JSON
                invoice_items[idx] = dict(inv_item)
                invoice_items[idx]['returned_qty'] = already_returned + return_qty
                processed += 1

                # Restock the exact variant that was sold — variant_id stored at invoice creation.
                # If variant_id is missing (old invoice), auto-resolve when only 1 variant exists.
                variant_id = str(inv_item.get('variant_id', '')).strip()
                product_id = str(inv_item.get('product_id', '')).strip()
                item_name  = inv_item.get('name', f'item {idx}')

                if product_id and not variant_id:
                    pv_qs = ProductVariant.objects.filter(product_id=product_id)
                    if pv_qs.count() == 1:
                        variant_id = str(pv_qs.first().id)
                    elif pv_qs.exists():
                        errors.append(
                            f'"{item_name}": return recorded but stock not updated — '
                            f'variant not stored in this invoice. Edit stock manually.'
                        )

                if variant_id and product_id:
                    try:
                        variant = ProductVariant.objects.select_for_update().get(
                            id=variant_id, product_id=product_id,
                        )
                        note = f'{reason_label} — Invoice {invoice_label}'
                        InventoryService.update_stock(
                            variant=variant,
                            new_qty=variant.stock_quantity + return_qty,
                            changed_by=request.user,
                            reason=StockMovementReason.RETURN_FROM_CUSTOMER,
                            note=note,
                        )
                        restocked += 1
                    except ProductVariant.DoesNotExist:
                        errors.append(f'"{item_name}": variant not found — stock not updated')

            invoice.items = invoice_items
            invoice.save(update_fields=['items'])

        http_status = status.HTTP_200_OK if processed > 0 else status.HTTP_400_BAD_REQUEST
        return Response({
            'processed': processed,
            'restocked': restocked,
            'errors':    errors,
            'invoice':   InvoiceSerializer(invoice).data,
        }, status=http_status)


class CustomerPurchaseHistoryView(APIView):
    """
    GET /api/v1/stores/purchases/
    Returns all invoices where customer_ns_code matches the authenticated customer's profile_id.
    Used on the customer-facing Purchase History screen.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Customer purchase history',
        responses={200: CustomerInvoiceSerializer(many=True)},
    )
    def get(self, request):
        profile_id = getattr(request.user, 'profile_id', None)
        if not profile_id:
            return Response({'results': [], 'count': 0})
        invoices  = (
            Invoice.objects
            .filter(customer_ns_code__iexact=profile_id)
            .select_related('store')
            .order_by('-created_at')
        )
        count     = invoices.count()
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 50)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        offset    = (page - 1) * page_size
        return Response({
            'results': CustomerInvoiceSerializer(invoices[offset:offset + page_size], many=True).data,
            'count':   count,
        })


class InvoiceExportView(APIView):
    """
    GET /api/v1/stores/mine/invoices/export/?period=daily&format=csv
    Exports vendor invoices for a period as CSV or PDF (one row per line item).
    period: daily | weekly | monthly
    format: csv  | pdf
    """
    permission_classes = [IsAuthenticated, IsVendor]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _period_range(period):
        from datetime import timedelta
        from django.utils.timezone import now
        today = now().date()
        if period == 'daily':
            start = now().replace(hour=0, minute=0, second=0, microsecond=0)
            label = f"Daily_{today}"
        elif period == 'weekly':
            start = now() - timedelta(days=today.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            label = f"Weekly_{start.date()}_to_{today}"
        else:
            start = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            label = f"Monthly_{today.strftime('%B_%Y')}"
        return start, label, today

    @staticmethod
    def _product_meta(product_ids):
        """Return {product_id_str: (category, subcategory)} for a set of IDs."""
        from apps.products.models import Product
        qs = Product.objects.filter(id__in=product_ids).values('id', 'category', 'subcategory')
        return {str(p['id']): (p['category'] or '', p['subcategory'] or '') for p in qs}

    @staticmethod
    def _discount_label(inv):
        if inv.discount_type == 'percent':
            return f"{inv.discount_value}%"
        if inv.discount_type == 'amount':
            return f"Rs.{inv.discount_value}"
        return '-'

    @staticmethod
    def _build_rows(invoices, product_meta):
        """
        One row per line item (Shopify/QuickBooks style).
        Returns list of dicts with all fields.
        """
        rows = []
        for inv in invoices:
            inv_id      = str(inv.id)[:8].upper()
            date        = inv.created_at.strftime('%d %b %Y %H:%M')
            customer    = inv.customer_name
            phone       = inv.customer_phone
            ns_code     = inv.customer_ns_code or '-'
            discount    = InvoiceExportView._discount_label(inv)
            inv_total   = float(inv.total)
            notes       = inv.notes or ''

            for it in (inv.items or []):
                pid          = str(it.get('product_id', '') or '')
                cat, subcat  = product_meta.get(pid, ('', ''))
                qty          = int(it.get('qty', 1))
                unit_price   = float(it.get('price', 0))
                item_total   = qty * unit_price
                rows.append({
                    'inv_id':     inv_id,
                    'date':       date,
                    'customer':   customer,
                    'phone':      phone,
                    'ns_code':    ns_code,
                    'category':   cat,
                    'subcategory':subcat,
                    'product_id': pid or '-',
                    'product':    it.get('name', ''),
                    'qty':        qty,
                    'unit_price': unit_price,
                    'item_total': item_total,
                    'discount':   discount,
                    'inv_total':  inv_total,
                    'notes':      notes,
                })
        return rows

    # ------------------------------------------------------------------
    # Main handler
    # ------------------------------------------------------------------
    def get(self, request):
        import csv
        import io
        from django.http import HttpResponse
        from django.utils.timezone import now

        if not hasattr(request.user, 'store'):
            return Response({'error': 'no_store'}, status=status.HTTP_400_BAD_REQUEST)

        period    = request.query_params.get('period', 'monthly')
        fmt       = request.query_params.get('format', 'csv').lower()
        store     = request.user.store
        start, label, today = self._period_range(period)

        invoices = list(
            Invoice.objects
            .filter(store=store, created_at__gte=start)
            .order_by('created_at')
        )

        # Collect all product IDs across all invoices for a single DB lookup
        all_pids = {
            str(it.get('product_id', ''))
            for inv in invoices
            for it in (inv.items or [])
            if it.get('product_id')
        }
        product_meta = self._product_meta(all_pids)
        rows         = self._build_rows(invoices, product_meta)

        store_safe = store.name.replace(' ', '_')
        filename   = f"{store_safe}_Sales_{label}"

        period_label = {'daily': 'Today', 'weekly': 'This Week', 'monthly': 'This Month'}.get(period, period.title())
        grand_total  = sum(float(inv.total) for inv in invoices)
        total_items  = sum(int(it.get('qty', 1)) for inv in invoices for it in (inv.items or []))

        # ── CSV ───────────────────────────────────────────────────────────────
        if fmt == 'csv':
            buf    = io.StringIO()
            writer = csv.writer(buf)

            # Report header block
            writer.writerow([f"Sales Report — {store.name}"])
            writer.writerow([f"Period: {period_label}  |  Generated: {today.strftime('%d %b %Y')}"])
            writer.writerow([f"Total Invoices: {len(invoices)}  |  Total Items Sold: {total_items}  |  Grand Total: Rs.{grand_total:.2f}"])
            writer.writerow([])

            # Column headers
            writer.writerow([
                'Invoice ID', 'Date', 'Customer Name', 'Phone', 'NS Code',
                'Category', 'Subcategory', 'Product ID', 'Product Name',
                'Qty', 'Unit Price (Rs.)', 'Item Total (Rs.)',
                'Discount', 'Invoice Total (Rs.)', 'Notes',
            ])

            for r in rows:
                writer.writerow([
                    r['inv_id'], r['date'], r['customer'], r['phone'], r['ns_code'],
                    r['category'], r['subcategory'], r['product_id'], r['product'],
                    r['qty'], f"{r['unit_price']:.2f}", f"{r['item_total']:.2f}",
                    r['discount'], f"{r['inv_total']:.2f}", r['notes'],
                ])

            writer.writerow([])
            writer.writerow(['', '', '', '', '', '', '', '', 'GRAND TOTAL',
                             total_items, '', f"{grand_total:.2f}", '', '', ''])

            resp = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            return resp

        # ── PDF ───────────────────────────────────────────────────────────────
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        BRAND     = colors.HexColor('#E91E63')
        BRAND_LT  = colors.HexColor('#FCE4EC')
        GREY      = colors.HexColor('#757575')
        STRIPE    = colors.HexColor('#FFF8F9')
        HEADER_BG = colors.HexColor('#212121')

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=landscape(A4),
            leftMargin=12*mm, rightMargin=12*mm,
            topMargin=12*mm, bottomMargin=12*mm,
        )
        styles = getSampleStyleSheet()

        s_title  = ParagraphStyle('nk_title',  fontSize=18, fontName='Helvetica-Bold', textColor=BRAND, spaceAfter=2)
        s_sub    = ParagraphStyle('nk_sub',    fontSize=9,  fontName='Helvetica',      textColor=GREY,  spaceAfter=10)
        s_label  = ParagraphStyle('nk_label',  fontSize=8,  fontName='Helvetica-Bold', textColor=GREY)
        s_value  = ParagraphStyle('nk_value',  fontSize=10, fontName='Helvetica-Bold', textColor=HEADER_BG)
        s_footer = ParagraphStyle('nk_footer', fontSize=7,  fontName='Helvetica',      textColor=GREY, alignment=TA_CENTER)
        s_cell   = ParagraphStyle('nk_cell',   fontSize=7,  fontName='Helvetica',      leading=9)
        s_cell_b = ParagraphStyle('nk_cell_b', fontSize=7,  fontName='Helvetica-Bold', leading=9)

        elements = []

        # ── Page header ──────────────────────────────────────────────
        elements.append(Paragraph(f"{store.name}", s_title))
        elements.append(Paragraph(
            f"Sales Report  •  {period_label}  •  Generated {today.strftime('%d %B %Y')}",
            s_sub,
        ))
        elements.append(HRFlowable(width='100%', thickness=1, color=BRAND, spaceAfter=8))

        # ── Summary KPI boxes ─────────────────────────────────────────
        kpi_data = [[
            Paragraph('TOTAL INVOICES', s_label),
            Paragraph('ITEMS SOLD', s_label),
            Paragraph('GROSS REVENUE', s_label),
            Paragraph('NET REVENUE', s_label),
        ], [
            Paragraph(str(len(invoices)), s_value),
            Paragraph(str(total_items), s_value),
            Paragraph(f"Rs.{sum(sum(float(it.get('price',0))*int(it.get('qty',1)) for it in (inv.items or [])) for inv in invoices):.2f}", s_value),
            Paragraph(f"Rs.{grand_total:.2f}", s_value),
        ]]
        kpi_widths = [doc.width / 4] * 4
        kpi_table  = Table(kpi_data, colWidths=kpi_widths)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,-1), BRAND_LT),
            ('ROUNDEDCORNERS', [4]),
            ('BOX',          (0,0), (-1,-1), 0.5, BRAND),
            ('LINEAFTER',    (0,0), (2,-1),  0.5, BRAND),
            ('TOPPADDING',   (0,0), (-1,-1), 6),
            ('BOTTOMPADDING',(0,0), (-1,-1), 6),
            ('LEFTPADDING',  (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 6*mm))

        # ── Item table ────────────────────────────────────────────────
        col_headers = [
            'Invoice ID', 'Date & Time', 'Customer', 'NS Code',
            'Category', 'Sub-category', 'Product ID', 'Product Name',
            'Qty', 'Unit Price', 'Item Total', 'Discount', 'Inv. Total', 'Notes',
        ]
        tdata = [[Paragraph(h, s_cell_b) for h in col_headers]]

        for r in rows:
            tdata.append([
                Paragraph(r['inv_id'],     s_cell),
                Paragraph(r['date'],       s_cell),
                Paragraph(f"{r['customer']}\n{r['phone']}", s_cell),
                Paragraph(r['ns_code'],    s_cell),
                Paragraph(r['category'],   s_cell),
                Paragraph(r['subcategory'],s_cell),
                Paragraph(r['product_id'][:12], s_cell),
                Paragraph(r['product'],    s_cell),
                Paragraph(str(r['qty']),   s_cell),
                Paragraph(f"Rs.{r['unit_price']:.2f}", s_cell),
                Paragraph(f"Rs.{r['item_total']:.2f}", s_cell),
                Paragraph(r['discount'],   s_cell),
                Paragraph(f"Rs.{r['inv_total']:.2f}", s_cell),
                Paragraph(r['notes'][:40] if r['notes'] else '-', s_cell),
            ])

        # Grand total row
        tdata.append([
            Paragraph('', s_cell_b),
            Paragraph('', s_cell_b),
            Paragraph(f"{len(invoices)} invoice(s)", s_cell_b),
            Paragraph('', s_cell_b),
            Paragraph('', s_cell_b),
            Paragraph('', s_cell_b),
            Paragraph('', s_cell_b),
            Paragraph('GRAND TOTAL', s_cell_b),
            Paragraph(str(total_items), s_cell_b),
            Paragraph('', s_cell_b),
            Paragraph(f"Rs.{grand_total:.2f}", s_cell_b),
            Paragraph('', s_cell_b),
            Paragraph('', s_cell_b),
            Paragraph('', s_cell_b),
        ])

        page_w = doc.width
        col_widths = [
            18*mm, 22*mm, 32*mm, 22*mm,   # inv_id, date, customer, ns_code
            20*mm, 20*mm, 24*mm, 35*mm,   # cat, subcat, product_id, product name
            10*mm, 18*mm, 18*mm,           # qty, unit, item_total
            16*mm, 18*mm, 25*mm,           # discount, inv_total, notes
        ]
        item_table = Table(tdata, colWidths=col_widths, repeatRows=1)
        item_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND',    (0,0), (-1,0), HEADER_BG),
            ('TEXTCOLOR',     (0,0), (-1,0), colors.white),
            ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0), (-1,0), 7),
            # Data rows
            ('FONTSIZE',      (0,1), (-1,-2), 7),
            ('ROWBACKGROUNDS',(0,1), (-1,-2), [colors.white, STRIPE]),
            # Grand total row
            ('BACKGROUND',    (0,-1), (-1,-1), BRAND_LT),
            ('FONTNAME',      (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('LINEABOVE',     (0,-1), (-1,-1), 1, BRAND),
            # Right-align numeric columns
            ('ALIGN',         (8,0), (-1,-1), 'RIGHT'),
            # Grid
            ('GRID',          (0,0), (-1,-2), 0.25, colors.HexColor('#E0E0E0')),
            ('LINEBELOW',     (0,0), (-1,0),  0.5,  BRAND),
            # Padding
            ('TOPPADDING',    (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING',   (0,0), (-1,-1), 3),
            ('RIGHTPADDING',  (0,0), (-1,-1), 3),
            ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 6*mm))
        elements.append(HRFlowable(width='100%', thickness=0.5, color=GREY))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            f"Generated by NearKart  •  {store.name}  •  {today.strftime('%d %B %Y')}  •  Confidential",
            s_footer,
        ))

        doc.build(elements)
        buf.seek(0)
        resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return resp


class VendorStoresListView(APIView):
    """
    GET /api/v1/stores/mine/all/
    Returns all stores owned by the authenticated vendor.
    Supports multi-location vendors — display-only, no store-switching.
    """
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='List all vendor stores',
        responses={200: StoreListSerializer(many=True)},
    )
    def get(self, request):
        stores = annotate_stores_with_subcategories(
            list(Store.objects.filter(owner=request.user, is_active=True).order_by('created_at'))
        )
        return Response({
            'count':   len(stores),
            'results': StoreListSerializer(stores, many=True).data,
        })


class StoreLocationsView(APIView):
    """
    GET /api/v1/stores/<store_id>/locations/
    Returns all other active locations owned by the same vendor.
    Used on the customer-facing store detail page to show "More Locations".
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Other locations by same vendor',
        responses={200: StoreListSerializer(many=True)},
    )
    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'count': 0, 'results': []})
        siblings = annotate_stores_with_subcategories(
            list(
                Store.objects
                .filter(owner=store.owner, is_active=True)
                .exclude(id=store_id)
                .order_by('created_at')
            )
        )
        return Response({
            'count':   len(siblings),
            'results': StoreListSerializer(siblings, many=True).data,
        })


# ── Website Request ────────────────────────────────────────────────────────────

_WEBSITE_CRITERIA = [
    {
        'key':         'account_age',
        'label':       'Account active for 30+ days',
        'description': 'Your NearSpot account must be at least 30 days old',
        'required':    '30 days',
    },
    {
        'key':         'store_verified',
        'label':       'Store verified by NearSpot',
        'description': 'Your store must be verified by the NearSpot team',
        'required':    'Verified',
    },
    {
        'key':         'store_complete',
        'label':       'Store profile complete',
        'description': 'Logo, banner, and description must all be filled',
        'required':    'Complete',
    },
    {
        'key':         'products_listed',
        'label':       '10+ active products',
        'description': 'Your store must have at least 10 active products listed',
        'required':    '10',
    },
    {
        'key':         'reviews_quality',
        'label':       '5+ reviews with 4.0★ average',
        'description': 'At least 5 customer reviews with an average rating of 4.0 or higher',
        'required':    '5 reviews / 4.0★',
    },
    {
        'key':         'referrals_done',
        'label':       '3+ completed referrals',
        'description': 'You must have referred at least 3 people using your NS code',
        'required':    '3',
    },
    {
        'key':         'reservations_completed',
        'label':       '5+ completed reservations',
        'description': 'Your store must have fulfilled at least 5 customer reservations',
        'required':    '5',
    },
]


def _check_eligibility(user):
    from django.db.models import Avg
    from apps.loyalty.models import Referral
    from apps.reservations.models import ReservationStatus

    try:
        store = user.store
    except AttributeError:
        return False, []

    try:
        product_count = store.products.filter(status='active').count()
    except Exception:
        product_count = 0

    try:
        review_qs    = store.reviews.all()
        review_count = review_qs.count()
        avg_rating   = review_qs.aggregate(avg=Avg('rating'))['avg'] or 0.0
    except Exception:
        review_count, avg_rating = 0, 0.0

    try:
        referral_count = Referral.objects.filter(referrer=user, status=Referral.STATUS_COMPLETED).count()
    except Exception:
        referral_count = 0

    try:
        reservation_count = store.reservations.filter(status=ReservationStatus.COMPLETED).count()
    except Exception:
        reservation_count = 0

    account_age_days = max((tz.now() - user.created_at).days, 0)
    store_complete   = bool(store.logo_url and store.banner_url and store.description.strip())

    results = [
        {'key': 'account_age',           'met': account_age_days >= 30,  'current': f'{account_age_days} days'},
        {'key': 'store_verified',        'met': store.is_verified,        'current': 'Verified' if store.is_verified else 'Not verified'},
        {'key': 'store_complete',        'met': store_complete,           'current': 'Complete' if store_complete else 'Incomplete'},
        {'key': 'products_listed',       'met': product_count >= 10,      'current': str(product_count)},
        {'key': 'reviews_quality',       'met': review_count >= 5 and avg_rating >= 4.0, 'current': f'{review_count} reviews / {avg_rating:.1f}★'},
        {'key': 'referrals_done',        'met': referral_count >= 3,      'current': str(referral_count)},
        {'key': 'reservations_completed','met': reservation_count >= 5,   'current': str(reservation_count)},
    ]

    # Merge static labels/descriptions into results
    label_map = {c['key']: c for c in _WEBSITE_CRITERIA}
    for r in results:
        meta = label_map[r['key']]
        r['label']       = meta['label']
        r['description'] = meta['description']
        r['required']    = meta['required']

    is_eligible = all(r['met'] for r in results)
    return is_eligible, results


class WebsiteRequestView(APIView):
    """
    GET  /api/v1/stores/mine/website-request/  — eligibility check + current request status
    POST /api/v1/stores/mine/website-request/  — submit website request
    """
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        is_eligible, criteria = _check_eligibility(request.user)
        existing = None
        try:
            store = request.user.store
            wr = store.website_request
            existing = {
                'id':                str(wr.id),
                'status':            wr.status,
                'domain_preference': wr.domain_preference,
                'admin_notes':       wr.admin_notes,
                'created_at':        wr.created_at.isoformat(),
            }
        except (AttributeError, WebsiteRequest.DoesNotExist):
            pass
        except Exception:
            # Table may not exist yet (migration pending) — return gracefully
            pass
        return Response({
            'is_eligible':    is_eligible,
            'criteria':       criteria,
            'existing_request': existing,
        })

    def post(self, request):
        is_eligible, criteria = _check_eligibility(request.user)
        if not is_eligible:
            unmet = [c['label'] for c in criteria if not c['met']]
            return Response(
                {'error': 'not_eligible', 'message': 'Complete all requirements first.', 'unmet': unmet},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            store = request.user.store
        except AttributeError:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)

        if hasattr(store, 'website_request'):
            return Response(
                {'error': 'already_submitted', 'message': 'You have already submitted a website request.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        domain = request.data.get('domain_preference', '').strip().lower()
        notes  = request.data.get('notes', '').strip()

        wr = WebsiteRequest.objects.create(store=store, domain_preference=domain, notes=notes)
        log_event('website_request', action='submitted', store_id=str(store.id), user_id=str(request.user.id))
        return Response({
            'id':                str(wr.id),
            'status':            wr.status,
            'domain_preference': wr.domain_preference,
            'created_at':        wr.created_at.isoformat(),
            'message':           'Your website request has been submitted. We will review it and get back to you.',
        }, status=status.HTTP_201_CREATED)


class StaffListCreateView(APIView):
    """
    GET  stores/mine/staff/  — list all staff members for the vendor's store
    POST stores/mine/staff/  — add a user as staff by phone number
    """
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='List store staff members')
    def get(self, request):
        try:
            store = request.user.store
        except AttributeError:
            return Response({'error': 'no_store'}, status=400)
        members = store.staff_members.filter(is_active=True).select_related('user').order_by('created_at')
        return Response(StaffMemberSerializer(members, many=True).data)

    @extend_schema(tags=[_TAG], summary='Add a staff member by phone number')
    def post(self, request):
        try:
            store = request.user.store
        except AttributeError:
            return Response({'error': 'no_store'}, status=400)

        phone = request.data.get('phone', '').strip()
        role  = request.data.get('role', StaffRole.STAFF)

        if not phone:
            return Response({'error': 'phone_required', 'message': 'Phone number is required.'}, status=400)
        if role not in StaffRole.values:
            return Response({'error': 'invalid_role', 'message': f'Role must be one of {StaffRole.values}.'}, status=400)

        from apps.auth_app.models import User
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response({'error': 'user_not_found', 'message': 'No NearKart account found with that phone number.'}, status=404)

        if user == request.user:
            return Response({'error': 'self_add', 'message': 'You cannot add yourself as staff.'}, status=400)

        member, created = StaffMember.objects.get_or_create(
            store=store, user=user,
            defaults={'role': role, 'invited_by': request.user, 'is_active': True},
        )
        if not created:
            if member.is_active:
                return Response({'error': 'already_staff', 'message': 'This user is already a staff member.'}, status=400)
            # Re-activate if previously removed
            member.is_active = True
            member.role = role
            member.invited_by = request.user
            member.save(update_fields=['is_active', 'role', 'invited_by'])

        log_event('staff_member', action='added', store_id=str(store.id), user_id=str(user.id), role=role)
        return Response(StaffMemberSerializer(member).data, status=status.HTTP_201_CREATED)


class StaffRemoveView(APIView):
    """DELETE stores/mine/staff/<staff_id>/ — deactivate a staff member"""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='Remove a staff member')
    def delete(self, request, staff_id):
        try:
            store = request.user.store
        except AttributeError:
            return Response({'error': 'no_store'}, status=400)

        try:
            member = StaffMember.objects.get(id=staff_id, store=store, is_active=True)
        except StaffMember.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)

        member.is_active = False
        member.save(update_fields=['is_active'])
        log_event('staff_member', action='removed', store_id=str(store.id), user_id=str(member.user.id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class StoreImagesUploadView(APIView):
    """POST stores/mine/images/ — upload logo and/or banner for the vendor's store."""
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request):
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import uuid, os

        try:
            store = request.user.store
        except AttributeError:
            return Response({'error': 'no_store'}, status=status.HTTP_400_BAD_REQUEST)

        _ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
        updated = {}
        for field in ('logo', 'banner'):
            file = request.FILES.get(field)
            if not file:
                continue
            if file.content_type not in _ALLOWED_IMAGE_TYPES:
                return Response({'error': 'invalid_file', 'message': f'{field}: file must be a valid image (JPEG, PNG, WebP, or GIF).'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                from PIL import Image
                import io as _io
                img = Image.open(file)
                img.verify()
                file.seek(0)
            except Exception:
                return Response({'error': 'invalid_file', 'message': f'{field}: file must be a valid image.'}, status=status.HTTP_400_BAD_REQUEST)
            ext = os.path.splitext(file.name)[1].lower() or '.jpg'
            filename = f'stores/{store.id}/{field}_{uuid.uuid4().hex}{ext}'
            path = default_storage.save(filename, ContentFile(file.read()))
            raw_url = default_storage.url(path)
            if raw_url.startswith('http'):
                url = raw_url.replace('http://', 'https://', 1)
            else:
                url = request.build_absolute_uri(raw_url).replace('http://', 'https://', 1)
            if field == 'logo':
                store.logo_url = url
                updated['logo_url'] = url
            else:
                store.banner_url = url
                updated['banner_url'] = url

        if not updated:
            return Response({'error': 'no_files', 'message': 'Provide at least one of: logo, banner.'}, status=status.HTTP_400_BAD_REQUEST)

        store.save(update_fields=list(updated.keys()) + ['updated_at'] if hasattr(store, 'updated_at') else list(updated.keys()))
        CacheService.invalidate_store(str(store.id))
        log_event('stores', action='images_uploaded', store_id=str(store.id), fields=list(updated.keys()))
        return Response(updated)


class VendorDiscountCodeListCreateView(APIView):
    """GET/POST stores/mine/discount-codes/ — vendor manages their discount codes."""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = request.user.store
        except AttributeError:
            return Response([], status=status.HTTP_200_OK)
        from .models import DiscountCode
        codes = DiscountCode.objects.filter(store=store).order_by('-created_at')[:200]
        return Response([_serialize_code(c) for c in codes])

    def post(self, request):
        try:
            store = request.user.store
        except AttributeError:
            return Response({'error': 'no_store'}, status=status.HTTP_400_BAD_REQUEST)
        from .models import DiscountCode
        data = request.data
        code_str = str(data.get('code', '')).upper().strip()
        if not code_str:
            return Response({'error': 'code_required'}, status=status.HTTP_400_BAD_REQUEST)
        if DiscountCode.objects.filter(store=store, code=code_str).exists():
            return Response({'error': 'code_exists', 'message': f'Code {code_str} already exists for this store.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            value = float(data.get('value', 0))
            assert value > 0
        except (TypeError, ValueError, AssertionError):
            return Response({'error': 'invalid_value'}, status=status.HTTP_400_BAD_REQUEST)
        discount_type = data.get('discount_type', 'percent')
        if discount_type not in ('percent', 'flat'):
            return Response({'error': 'invalid_type'}, status=status.HTTP_400_BAD_REQUEST)
        if discount_type == 'percent' and value > 100:
            return Response({'error': 'invalid_value', 'message': 'Percent discount cannot exceed 100.'}, status=status.HTTP_400_BAD_REQUEST)
        code = DiscountCode.objects.create(
            store=store,
            code=code_str,
            description=data.get('description', ''),
            discount_type=discount_type,
            value=value,
            min_order_amount=data.get('min_order_amount') or None,
            max_uses=data.get('max_uses') or None,
            valid_from=data.get('valid_from') or None,
            valid_till=data.get('valid_till') or None,
            is_active=data.get('is_active', True),
            created_by=request.user,
        )
        log_event('stores', action='discount_code_created', store_id=str(store.id), code=code_str)
        return Response(_serialize_code(code), status=status.HTTP_201_CREATED)


class VendorDiscountCodeUpdateView(APIView):
    """PATCH/DELETE stores/mine/discount-codes/<id>/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_code(self, request, code_id):
        from .models import DiscountCode
        try:
            store = request.user.store
        except AttributeError:
            return None, Response({'error': 'no_store'}, status=400)
        try:
            return DiscountCode.objects.get(id=code_id, store=store), None
        except DiscountCode.DoesNotExist:
            return None, Response({'error': 'not_found'}, status=404)

    def patch(self, request, code_id):
        code, err = self._get_code(request, code_id)
        if err:
            return err
        data = request.data
        for field in ('description', 'discount_type', 'min_order_amount', 'valid_from', 'valid_till', 'is_active', 'max_uses'):
            if field in data:
                setattr(code, field, data[field] if data[field] != '' else None)
        if 'value' in data:
            try:
                code.value = float(data['value'])
            except (TypeError, ValueError):
                return Response({'error': 'invalid_value'}, status=400)
        code.save()
        return Response(_serialize_code(code))

    def delete(self, request, code_id):
        code, err = self._get_code(request, code_id)
        if err:
            return err
        code.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplyDiscountCodeView(APIView):
    """POST stores/<store_id>/apply-discount/ — validate a code and calculate the discount."""
    permission_classes = [IsAuthenticated]

    def post(self, request, store_id):
        from .models import DiscountCode
        code_str = str(request.data.get('code', '')).upper().strip()
        try:
            order_amount = float(request.data.get('order_amount', 0))
        except (TypeError, ValueError):
            order_amount = 0

        try:
            code = DiscountCode.objects.get(store_id=store_id, code=code_str)
        except DiscountCode.DoesNotExist:
            return Response({'valid': False, 'error': 'code_not_found', 'message': 'Invalid discount code.'})

        valid, reason = code.is_valid(order_amount or None)
        if not valid:
            messages = {
                'code_inactive':    'This code is no longer active.',
                'max_uses_reached': 'This code has reached its usage limit.',
                'not_started':      'This code is not active yet.',
                'expired':          'This code has expired.',
                'below_minimum':    f'Minimum order amount is ₹{code.min_order_amount}.',
            }
            return Response({'valid': False, 'error': reason, 'message': messages.get(reason, 'Code cannot be applied.')})

        discount_amount = code.calculate_discount(order_amount) if order_amount else 0
        # NOTE: uses_count must be incremented only when an invoice is actually created,
        # NOT here — incrementing here burns single-use codes on validation preview.
        return Response({
            'valid':           True,
            'code':            code.code,
            'discount_type':   code.discount_type,
            'value':           str(code.value),
            'discount_amount': discount_amount,
            'final_amount':    max(0, round(order_amount - discount_amount, 2)),
            'description':     code.description,
        })


def _serialize_code(c):
    return {
        'id':               str(c.id),
        'code':             c.code,
        'description':      c.description,
        'discount_type':    c.discount_type,
        'value':            str(c.value),
        'min_order_amount': str(c.min_order_amount) if c.min_order_amount else None,
        'max_uses':         c.max_uses,
        'uses_count':       c.uses_count,
        'valid_from':       str(c.valid_from) if c.valid_from else None,
        'valid_till':       str(c.valid_till) if c.valid_till else None,
        'is_active':        c.is_active,
        'created_at':       c.created_at.isoformat(),
    }


# ── Broadcast Channels ────────────────────────────────────────────────────────

def _serialize_channel(ch):
    return {
        'id':               str(ch.id),
        'name':             ch.name,
        'description':      ch.description,
        'auto_subscribe':   ch.auto_subscribe,
        'subscriber_count': ch.subscriber_count,
        'post_count':       ch.post_count,
        'created_at':       ch.created_at.isoformat(),
    }

def _serialize_post(p):
    return {
        'id':         str(p.id),
        'content':    p.content,
        'image_url':  p.image_url or None,
        'created_at': p.created_at.isoformat(),
    }


class VendorBroadcastChannelListCreateView(APIView):
    """GET/POST stores/mine/broadcast-channels/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = request.user.store
        except AttributeError:
            return Response([], status=status.HTTP_200_OK)
        channels = BroadcastChannel.objects.filter(store=store).order_by('-created_at')[:100]
        return Response([_serialize_channel(c) for c in channels])

    def post(self, request):
        try:
            store = request.user.store
        except AttributeError:
            return Response({'error': 'no_store'}, status=status.HTTP_400_BAD_REQUEST)
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'error': 'name_required'}, status=status.HTTP_400_BAD_REQUEST)
        channel = BroadcastChannel.objects.create(
            store=store,
            name=name,
            description=request.data.get('description', '').strip(),
            auto_subscribe=request.data.get('auto_subscribe', True),
        )
        log_event('broadcasts', action='channel_created', store_id=str(store.id), channel_id=str(channel.id))
        return Response(_serialize_channel(channel), status=status.HTTP_201_CREATED)


class VendorBroadcastChannelDetailView(APIView):
    """PATCH/DELETE stores/mine/broadcast-channels/{channel_id}/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_channel(self, request, channel_id):
        try:
            store = request.user.store
        except AttributeError:
            return None
        return BroadcastChannel.objects.filter(id=channel_id, store=store).first()

    def patch(self, request, channel_id):
        channel = self._get_channel(request, channel_id)
        if not channel:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        name = request.data.get('name', '').strip()
        if name:
            channel.name = name
        description = request.data.get('description')
        if description is not None:
            channel.description = description.strip()
        channel.save()
        return Response(_serialize_channel(channel))

    def delete(self, request, channel_id):
        channel = self._get_channel(request, channel_id)
        if not channel:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        channel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VendorBroadcastPostListCreateView(APIView):
    """GET/POST stores/mine/broadcast-channels/{channel_id}/posts/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_channel(self, request, channel_id):
        try:
            store = request.user.store
        except AttributeError:
            return None
        return BroadcastChannel.objects.filter(id=channel_id, store=store).first()

    def get(self, request, channel_id):
        channel = self._get_channel(request, channel_id)
        if not channel:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        posts     = channel.posts.order_by('-created_at')
        count     = posts.count()
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 50)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        offset    = (page - 1) * page_size
        return Response({'results': [_serialize_post(p) for p in posts[offset:offset + page_size]], 'count': count})

    def post(self, request, channel_id):
        channel = self._get_channel(request, channel_id)
        if not channel:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'content_required'}, status=status.HTTP_400_BAD_REQUEST)
        post = BroadcastPost.objects.create(channel=channel, content=content)
        log_event('broadcasts', action='post_created', channel_id=str(channel.id))
        return Response(_serialize_post(post), status=status.HTTP_201_CREATED)


class CustomerBroadcastChannelListView(APIView):
    """GET stores/{store_id}/broadcast-channels/ — customer read-only"""
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        channels = BroadcastChannel.objects.filter(store__id=store_id, store__is_active=True).order_by('-created_at')[:100]
        return Response([_serialize_channel(c) for c in channels])


class CustomerBroadcastPostListView(APIView):
    """GET stores/{store_id}/broadcast-channels/{channel_id}/posts/ — customer read-only"""
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id, channel_id):
        channel = BroadcastChannel.objects.filter(id=channel_id, store__id=store_id, store__is_active=True).first()
        if not channel:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        posts     = channel.posts.order_by('-created_at')
        count     = posts.count()
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 50)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        offset    = (page - 1) * page_size
        return Response({'results': [_serialize_post(p) for p in posts[offset:offset + page_size]], 'count': count})


class CustomerBlockStoreView(APIView):
    """POST /stores/{id}/block/ — customer toggles block on a store."""
    permission_classes = [IsAuthenticated]

    def post(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)

        entry, created = CustomerBlockedStore.objects.get_or_create(customer=request.user, store=store)
        if not created:
            entry.delete()
            return Response({'is_blocked': False, 'message': 'Store unblocked.'})
        return Response({'is_blocked': True, 'message': 'Store blocked. It will no longer appear in your feed.'})

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        is_blocked = CustomerBlockedStore.objects.filter(customer=request.user, store=store).exists()
        return Response({'is_blocked': is_blocked})


class MonthlyEarningsPDFView(APIView):
    """GET /stores/mine/earnings/pdf/?month=YYYY-MM — download monthly earnings report."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Monthly earnings PDF',
        description='Returns a PDF report of all invoices for the given month (YYYY-MM).',
        parameters=[OpenApiParameter('month', str, description='Month in YYYY-MM format', required=True)],
    )
    def get(self, request):
        try:
            store = request.user.store
        except Exception:
            return Response({'error': 'no_store'}, status=400)

        month_str = request.query_params.get('month', '')
        try:
            from datetime import datetime
            month_dt = datetime.strptime(month_str, '%Y-%m')
        except ValueError:
            return Response({'error': 'validation_error', 'message': 'month must be YYYY-MM format.'}, status=400)

        from django.utils import timezone
        import calendar
        from decimal import Decimal
        year, month = month_dt.year, month_dt.month
        last_day = calendar.monthrange(year, month)[1]
        period_start = timezone.datetime(year, month, 1, tzinfo=timezone.utc)
        period_end   = timezone.datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

        invoices = Invoice.objects.filter(
            store=store,
            created_at__gte=period_start,
            created_at__lte=period_end,
        ).order_by('created_at')

        total_revenue = sum(inv.total for inv in invoices) if invoices else Decimal('0')

        # ── Generate PDF ────────────────────────────────────────────────────────
        import io
        from django.http import HttpResponse
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        bold   = ParagraphStyle('bold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12)
        normal = ParagraphStyle('normal', parent=styles['Normal'], fontName='Helvetica', fontSize=9)
        center = ParagraphStyle('center', parent=bold, alignment=TA_CENTER, fontSize=16)
        sub    = ParagraphStyle('sub', parent=styles['Normal'], fontName='Helvetica', fontSize=10, alignment=TA_CENTER)

        navy   = colors.HexColor('#1E3A5F')
        light  = colors.HexColor('#F0F4F8')

        story  = []
        story.append(Paragraph('NearSpot', center))
        story.append(Paragraph(f'Monthly Earnings Report', sub))
        story.append(Paragraph(f'{store.name} · {month_dt.strftime("%B %Y")}', sub))
        story.append(Spacer(1, 8*mm))

        # Summary box
        summary_data = [
            ['Total Invoices', 'Total Revenue'],
            [str(invoices.count()), f'₹{total_revenue:,.2f}'],
        ]
        summary_tbl = Table(summary_data, colWidths=[85*mm, 85*mm])
        summary_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), navy),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, 1), light),
            ('FONTNAME',   (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 1), (-1, 1), 14),
            ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [None]),
            ('BOX',        (0, 0), (-1, -1), 0.5, colors.grey),
            ('INNERGRID',  (0, 0), (-1, -1), 0.25, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_tbl)
        story.append(Spacer(1, 8*mm))

        # Invoice rows
        header = ['#', 'Invoice No.', 'Customer', 'Date', 'Amount']
        rows   = [header]
        for idx, inv in enumerate(invoices, start=1):
            rows.append([
                str(idx),
                f'#{str(inv.id)[:8].upper()}',
                inv.customer_name[:25],
                inv.created_at.strftime('%d %b %Y'),
                f'₹{inv.total:,.2f}',
            ])

        tbl = Table(rows, colWidths=[10*mm, 40*mm, 60*mm, 35*mm, 30*mm])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), navy),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, -1), 8),
            ('ALIGN',      (4, 0), (4, -1), 'RIGHT'),
            ('ALIGN',      (0, 0), (0, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light]),
            ('BOX',        (0, 0), (-1, -1), 0.5, colors.grey),
            ('INNERGRID',  (0, 0), (-1, -1), 0.25, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        doc.build(story)

        filename = f'{store.name.replace(" ", "_")}_{month_str}_earnings'
        resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return resp


# ── Service Catalogue ─────────────────────────────────────────────────────────

class ServiceCatalogueListCreateView(APIView):
    """
    GET  /stores/mine/services/  — list services for the vendor's store
    POST /stores/mine/services/  — create a new service entry
    """
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='List service catalogue (vendor)', responses={200: ServiceCatalogueSerializer(many=True)})
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'results': [], 'count': 0})
        services = ServiceCatalogue.objects.filter(store=request.user.store)
        return Response({'results': ServiceCatalogueSerializer(services, many=True).data, 'count': services.count()})

    @extend_schema(tags=[_TAG], summary='Create service catalogue entry (vendor)', request=ServiceCatalogueSerializer, responses={201: ServiceCatalogueSerializer})
    def post(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ServiceCatalogueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = serializer.save(store=request.user.store)
        return Response(ServiceCatalogueSerializer(service).data, status=status.HTTP_201_CREATED)


class ServiceCatalogueDetailView(APIView):
    """
    GET    /stores/mine/services/<service_id>/  — retrieve a service
    PUT    /stores/mine/services/<service_id>/  — update a service
    DELETE /stores/mine/services/<service_id>/  — delete a service
    """
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_service(self, request, service_id):
        if not hasattr(request.user, 'store'):
            return None
        try:
            return ServiceCatalogue.objects.get(id=service_id, store=request.user.store)
        except ServiceCatalogue.DoesNotExist:
            return None

    @extend_schema(tags=[_TAG], summary='Retrieve a service catalogue entry', responses={200: ServiceCatalogueSerializer})
    def get(self, request, service_id):
        service = self._get_service(request, service_id)
        if service is None:
            return Response({'error': 'not_found', 'message': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ServiceCatalogueSerializer(service).data)

    @extend_schema(tags=[_TAG], summary='Update a service catalogue entry', request=ServiceCatalogueSerializer, responses={200: ServiceCatalogueSerializer})
    def put(self, request, service_id):
        service = self._get_service(request, service_id)
        if service is None:
            return Response({'error': 'not_found', 'message': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ServiceCatalogueSerializer(service, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(tags=[_TAG], summary='Delete a service catalogue entry', responses={204: None})
    def delete(self, request, service_id):
        service = self._get_service(request, service_id)
        if service is None:
            return Response({'error': 'not_found', 'message': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Vendor Mini-Website (#Area32) ─────────────────────────────────────────────

class StorePublicWebsiteView(APIView):
    """GET /stores/s/<slug>/ — public vendor mini-website data (no auth required).
    Returns store info, products, hours, active offers, and recent reviews."""
    permission_classes = []  # public endpoint

    def get(self, request, slug):
        from apps.products.models import Product
        from apps.products.serializers import ProductListSerializer

        try:
            store = (
                Store.objects
                .prefetch_related('hours', 'photos')
                .get(slug=slug, is_active=True)
            )
        except Store.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)

        # Base store data
        from django.db.models import Avg, Count
        store_agg = StoreReview.objects.filter(store=store).aggregate(
            avg_rating=Avg('rating'),
            review_count=Count('id'),
        )

        hours_data = StoreHoursSerializer(store.hours.all(), many=True).data
        offers_data = StoreOfferSerializer(
            StoreOffer.objects.filter(store=store, is_active=True)[:5],
            many=True,
        ).data
        reviews_data = StoreReviewSerializer(
            StoreReview.objects.filter(store=store, is_flagged=False)
                .select_related('user')
                .order_by('-created_at')[:5],
            many=True,
            context={'request': request},
        ).data

        products_qs = (
            Product.objects
            .filter(store=store, is_visible=True, status='active')
            .prefetch_related('images', 'variants')
            .order_by('-created_at')[:20]
        )
        products_data = ProductListSerializer(products_qs, many=True, context={'request': request}).data

        return Response({
            'id':          str(store.id),
            'slug':        store.slug,
            'name':        store.name,
            'description': store.description,
            'category':    store.category,
            'logo_url':    store.logo_url,
            'banner_url':  store.banner_url,
            'phone':       store.phone,
            'address':     store.address,
            'locality':    store.locality,
            'city':        store.city,
            'state':       store.state,
            'is_open':     store.is_open,
            'is_verified': store.is_verified,
            'is_women_owned': store.is_women_owned,
            'is_home_based':  store.is_home_based,
            'rating':       round(store_agg['avg_rating'] or 0, 1),
            'review_count': store_agg['review_count'] or 0,
            'hours':        hours_data,
            'offers':       offers_data,
            'products':     products_data,
            'reviews':      reviews_data,
        })
