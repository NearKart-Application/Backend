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
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse, inline_serializer
import rest_framework.serializers as s

from core.permissions import IsVendor, IsStoreOwner
from core.utils.cache import CacheService
from apps.blacklist.services import BlacklistService
from .models import Store, StoreHours
from .serializers import StoreSerializer, StoreListSerializer, StoreReviewSerializer, StoreHoursSerializer
from .services import StoreService, QRService

logger = logging.getLogger(__name__)

_TAG = 'Stores'


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
        return Response(StoreListSerializer(stores, many=True).data)


class StoreDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=[_TAG], summary='Get store detail', responses={200: StoreSerializer}, auth=[])
    def get(self, request, store_id):
        cached = CacheService.get(CacheService.store_detail_key(str(store_id)))
        if cached:
            return Response(cached)
        try:
            store = Store.objects.prefetch_related('hours', 'reviews').get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = StoreSerializer(store).data
        CacheService.set(CacheService.store_detail_key(str(store_id)), data, timeout=CacheService.TTL_STORE_DETAIL)
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
            from apps.auth_app.models import User
            from apps.notifications.services import NotificationService
            follower_ids = StoreFollow.objects.filter(store=store).values_list('user_id', flat=True)
            followers = list(User.objects.filter(id__in=follower_ids))
            NotificationService.notify_store_opened(followers, store.name, str(store.id))
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
        return Response({'followed': followed, 'message': msg})


class StoreReviewView(APIView):
    permission_classes = [IsAuthenticated]

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
