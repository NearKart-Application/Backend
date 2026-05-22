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
from django.db import models
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse, inline_serializer
import rest_framework.serializers as s

from core.logging import log_event
from core.permissions import IsVendor, IsStoreOwner
from core.utils.cache import CacheService
from apps.blacklist.services import BlacklistService
from .models import Store, StoreHours, StoreOffer
from .serializers import (
    StoreSerializer, StoreListSerializer, StoreReviewSerializer,
    StoreReviewListSerializer, StoreOfferSerializer,
    StoreHoursSerializer, StoreMobileDetailSerializer,
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
            OpenApiParameter('category', str,    description='Filter by category',    required=False),
        ],
        responses={200: StoreListSerializer(many=True)},
        auth=[],
    )
    def get(self, request):
        try:
            lat      = float(request.query_params['lat'])
            lng      = float(request.query_params['lng'])
            radius   = int(request.query_params.get('radius', 2))
            category = request.query_params.get('category')
        except (KeyError, ValueError):
            return Response(
                {'error': 'validation_error', 'message': 'lat and lng are required numbers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stores = StoreService.get_nearby(lat, lng, radius_km=radius, category=category)
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
            return Response(cached)
        try:
            from django.db.models import Count, Avg, Prefetch
            from .models import StoreHours
            store = Store.objects.prefetch_related(
                Prefetch('hours', queryset=StoreHours.objects.all()),
                'followers',
            ).annotate(
                follower_count=Count('followers', distinct=True),
                avg_rating=Avg('reviews__rating'),
                review_count_ann=Count('reviews', distinct=True),
            ).get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = StoreMobileDetailSerializer(store, context={'request': request}).data
        # Cache the serialised response so subsequent requests are served from Redis
        CacheService.set(key, data, timeout=CacheService.TTL_STORE_DETAIL)
        # Algorithm 5 — HyperLogLog unique visitor tracking
        if request.user and request.user.is_authenticated:
            CacheService.record_store_visit(str(store_id), str(request.user.id))
        return Response(data)


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
        if hasattr(request.user, 'store'):
            return Response(
                {'error': 'validation_error', 'message': 'You already have a store.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
        reviews = store.reviews.select_related('user').order_by('-created_at')[:50]
        data = {'results': StoreReviewListSerializer(reviews, many=True).data, 'count': len(reviews)}
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
        serializer = StoreReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = StoreService.add_review(
            request.user, store,
            serializer.validated_data['rating'],
            serializer.validated_data.get('comment', ''),
        )
        CacheService.invalidate_store_reviews(str(store_id))
        return Response(StoreReviewSerializer(review).data)


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
        return Response(StoreHoursSerializer(sorted(hours, key=lambda h: h.day), many=True).data)


class StoreReviewListView(APIView):
    """GET /api/v1/stores/<id>/reviews/ — public list of reviews for a store."""
    permission_classes = [AllowAny]

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
        reviews = store.reviews.select_related('user').order_by('-created_at')[:50]
        data = {'results': StoreReviewListSerializer(reviews, many=True).data, 'count': len(reviews)}
        CacheService.set(key, data, timeout=CacheService.TTL_STORE_REVIEWS)
        return Response(data)


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
        from apps.stores.models import StoreFollow
        follower_ids = list(StoreFollow.objects.filter(store=store).values_list('user_id', flat=True))
        if follower_ids:
            disc = f' — {offer.discount_pct}% off' if offer.discount_pct else ''
            _dispatch_new_offer(follower_ids, store.name, offer.title + disc, str(store.id))
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
        limit = int(request.query_params.get('limit', 5))
        from apps.stores.models import StoreFollow
        store_ids = StoreFollow.objects.filter(user=request.user)\
            .order_by('-created_at').values_list('store_id', flat=True)[:limit]
        stores = Store.objects.filter(id__in=store_ids, is_active=True)
        return Response({'results': StoreListSerializer(stores, many=True).data, 'count': stores.count()})


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
        offer.is_active = False
        offer.save(update_fields=['is_active'])
        CacheService.invalidate_store_offers(str(store_id))
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
        active_res = Reservation.objects.filter(
            store=store, status__in=['pending', 'confirmed']
        ).count()
        return Response({
            'store_name':          store.name,
            'store_address':       store.address,
            'active_reservations': active_res,
            'total_products':      store.products.filter(is_active=True).count(),
            'follower_count':      store.followers.count(),
        })
