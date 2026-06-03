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
from core.utils.cache import CacheService
from apps.blacklist.services import BlacklistService
from django.utils import timezone as tz
from .models import Store, StoreHours, StoreOffer, Invoice, WebsiteRequest, StaffMember, StaffRole
from .serializers import (
    StoreSerializer, StoreListSerializer, StoreReviewSerializer,
    StoreReviewListSerializer, StoreOfferSerializer,
    StoreHoursSerializer, StoreMobileDetailSerializer, VendorReplySerializer,
    InvoiceSerializer, StaffMemberSerializer,
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
        # Gate: only customers with a completed reservation at this store can review
        from apps.reservations.models import Reservation, ReservationStatus
        has_completed = Reservation.objects.filter(
            customer=request.user, store=store, status=ReservationStatus.COMPLETED,
        ).exists()
        if not has_completed:
            return Response(
                {'error': 'no_completed_reservation',
                 'message': 'You can only review a store after completing a reservation there.'},
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
        # Notify vendor
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_new_review(store.owner, store.name, review.rating, str(store.id))
        except Exception:
            pass
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
        except (Store.DoesNotExist, store.reviews.model.DoesNotExist):
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
        return Response({'results': StoreReviewListSerializer(reviews, many=True).data, 'count': reviews.count()})


class MyReviewsView(APIView):
    """GET /api/v1/reviews/mine/ — all reviews written by the authenticated customer."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=[_TAG], summary='Get my reviews (customer)', responses={200: StoreReviewListSerializer(many=True)})
    def get(self, request):
        from .models import StoreReview
        reviews = StoreReview.objects.filter(user=request.user).select_related('store').order_by('-created_at')
        data = []
        for r in reviews:
            d = StoreReviewListSerializer(r).data
            d['store_id']   = str(r.store.id)
            d['store_name'] = r.store.name
            data.append(d)
        return Response({'results': data, 'count': len(data)})


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
            'total_products':      store.products.filter(status='active').count(),
            'follower_count':      store.followers.count(),
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
        invoices = Invoice.objects.filter(store=request.user.store)
        return Response({'results': InvoiceSerializer(invoices, many=True).data, 'count': invoices.count()})

    @extend_schema(tags=[_TAG], summary='Create invoice', request=InvoiceSerializer, responses={201: InvoiceSerializer})
    def post(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'error': 'no_store'}, status=status.HTTP_400_BAD_REQUEST)
        ser = InvoiceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        items = ser.validated_data.get('items', [])
        total = sum(float(i.get('price', 0)) * int(i.get('qty', 1)) for i in items)

        # If vendor provided a customer NS code, auto-fill name and mark as sent
        ns_code = ser.validated_data.get('customer_ns_code', '').strip().upper()
        customer_user = None
        if ns_code:
            from apps.auth_app.models import User
            try:
                customer_user = User.objects.get(profile_id=ns_code)
                ser.validated_data['customer_name'] = customer_user.get_full_name() or ser.validated_data.get('customer_name', '')
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
            for item in items:
                product_id = str(item.get('product_id', '')).strip()
                if product_id:
                    qty = max(1, int(item.get('qty', 1)))
                    InventoryService.deduct_for_invoice(
                        product_id=product_id,
                        qty=qty,
                        changed_by=request.user,
                        invoice_id=str(invoice.id),
                        store=request.user.store,
                    )

        if customer_user is not None:
            from apps.notifications.services import NotificationService
            store_name = request.user.store.name
            threading.Thread(
                target=NotificationService.notify_invoice_received,
                args=(customer_user, store_name, str(invoice.id), str(int(total))),
                daemon=True,
            ).start()

        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


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
        stores = Store.objects.filter(owner=request.user, is_active=True).order_by('created_at')
        return Response({
            'count':   stores.count(),
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
        siblings = (
            Store.objects
            .filter(owner=store.owner, is_active=True)
            .exclude(id=store_id)
            .order_by('created_at')
        )
        return Response({
            'count':   siblings.count(),
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
    {
        'key':         'active_subscription',
        'label':       'Active NearSpot subscription',
        'description': 'You must have an active paid subscription plan',
        'required':    'Active plan',
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
        has_sub = store.subscriptions.filter(is_active=True).exists()
    except Exception:
        has_sub = False

    try:
        product_count = store.products.filter(is_active=True).count()
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
        {'key': 'active_subscription',   'met': has_sub,                  'current': 'Active' if has_sub else 'No plan'},
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

        updated = {}
        for field in ('logo', 'banner'):
            file = request.FILES.get(field)
            if not file:
                continue
            ext = os.path.splitext(file.name)[1].lower() or '.jpg'
            filename = f'stores/{store.id}/{field}_{uuid.uuid4().hex}{ext}'
            path = default_storage.save(filename, ContentFile(file.read()))
            raw_url = default_storage.url(path)
            url = raw_url if raw_url.startswith('http') else f"{settings.SITE_URL.rstrip('/')}{raw_url}"
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
        codes = DiscountCode.objects.filter(store=store)
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
