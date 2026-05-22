"""
NearKart — Product Views
GET  /api/v1/products/nearby/
GET  /api/v1/products/search/
GET  /api/v1/products/<id>/
POST /api/v1/products/
PUT  /api/v1/products/<id>/
DELETE /api/v1/products/<id>/
POST /api/v1/products/<id>/wishlist/
"""
import logging
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse, inline_serializer
import rest_framework.serializers as s

from core.permissions import IsVendor, IsStoreOwner
from core.utils.cache import CacheService
from core.utils.upload_tracker import UploadTracker
from apps.billing.services import BillingService
from .models import Product
from .serializers import ProductSerializer, ProductListSerializer, MobileProductDetailSerializer
from .services import ProductService

logger = logging.getLogger(__name__)

_TAG = 'Products'


class NearbyProductsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Get nearby products',
        parameters=[
            OpenApiParameter('lat',      float, description='Latitude',               required=True),
            OpenApiParameter('lng',      float, description='Longitude',              required=True),
            OpenApiParameter('radius',   int,   description='Radius in km (1/2/3/5)', required=False),
            OpenApiParameter('category', str,   description='Filter by category',     required=False),
        ],
        responses={200: ProductListSerializer(many=True)},
        auth=[],
    )
    def get(self, request):
        try:
            lat      = float(request.query_params['lat'])
            lng      = float(request.query_params['lng'])
            radius   = int(request.query_params.get('radius', 2))
            category = request.query_params.get('category')
            store_id = request.query_params.get('store')
        except (KeyError, ValueError):
            return Response(
                {'error': 'validation_error', 'message': 'lat and lng are required numbers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        products = ProductService.get_nearby(lat, lng, radius_km=radius, category=category, store_id=store_id)
        data = ProductListSerializer(products, many=True, context={'request': request}).data
        return Response({'count': len(data), 'next': None, 'previous': None, 'results': data})


class ProductSearchView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Search products by name',
        parameters=[
            OpenApiParameter('q',      str,   description='Search query',  required=True),
            OpenApiParameter('lat',    float, description='Latitude',      required=False),
            OpenApiParameter('lng',    float, description='Longitude',     required=False),
            OpenApiParameter('radius', int,   description='Radius in km',  required=False),
        ],
        responses={200: ProductListSerializer(many=True)},
        auth=[],
    )
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {'error': 'validation_error', 'message': 'Search query q is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            lat    = float(request.query_params['lat']) if 'lat' in request.query_params else None
            lng    = float(request.query_params['lng']) if 'lng' in request.query_params else None
            radius = int(request.query_params.get('radius', 5))
        except ValueError:
            lat = lng = None
            radius = 5
        products = ProductService.search(query, lat, lng, radius)
        serialized = ProductListSerializer(products, many=True, context={'request': request}).data
        return Response({'count': len(serialized), 'next': None, 'previous': None, 'results': serialized})


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=[_TAG], summary='Get product detail', responses={200: ProductSerializer}, auth=[])
    def get(self, request, product_id):
        key    = CacheService.product_detail_key(str(product_id))
        cached = CacheService.get(key)
        if cached is not None:
            return Response(cached)
        try:
            product = Product.objects.select_related('store').prefetch_related('variants', 'images').get(
                id=product_id, is_visible=True, status='active',
            )
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = MobileProductDetailSerializer(product, context={'request': request}).data
        CacheService.set(key, data, timeout=CacheService.TTL_PRODUCT_DETAIL)
        return Response(data)


class ProductCreateView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Create product (vendor only)',
        request=ProductSerializer,
        responses={201: ProductSerializer},
        examples=[
            OpenApiExample(
                'Kurta with variants',
                request_only=True,
                value={
                    'name': 'Cotton Kurta',
                    'description': 'Handwoven cotton kurta for men, available in multiple sizes.',
                    'category': 'fashion',
                    'base_price': '499.00',
                    'status': 'active',
                    'is_visible': True,
                    'variants': [
                        {'name': 'Size S', 'sku': 'KT-S-001', 'price': '499.00', 'stock_quantity': 10},
                        {'name': 'Size M', 'sku': 'KT-M-001', 'price': '499.00', 'stock_quantity': 15},
                        {'name': 'Size L', 'sku': 'KT-L-001', 'price': '499.00', 'stock_quantity': 8},
                    ],
                },
            ),
            OpenApiExample(
                'Simple product (no variants)',
                request_only=True,
                value={
                    'name': 'Handmade Pickle — Mango',
                    'description': 'Traditional homemade mango pickle, 500g jar.',
                    'category': 'food',
                    'base_price': '149.00',
                    'status': 'active',
                    'is_visible': True,
                },
            ),
        ],
    )
    def post(self, request):
        if not hasattr(request.user, 'store'):
            return Response(
                {'error': 'validation_error', 'message': 'Create a store first before adding products.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        allowed, msg = BillingService.check_product_limit(request.user.store)
        if not allowed:
            return Response(
                {'error': 'plan_limit_reached', 'message': msg},
                status=status.HTTP_403_FORBIDDEN,
            )
        upload_allowed, upload_count = UploadTracker.check_and_increment(
            str(request.user.id),
            UploadTracker.MEDIA_PHOTO,
            getattr(settings, 'PHOTO_DAILY_UPLOAD_LIMIT', 50),
        )
        if not upload_allowed:
            return Response(
                {
                    'error': 'daily_limit_reached',
                    'message': (
                        f'Daily product creation limit reached ({upload_count} today). '
                        'Limit resets at midnight.'
                    ),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        serializer = ProductSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        product = ProductService.create(request.user.store, serializer.validated_data)
        return Response(ProductSerializer(product, context={'request': request}).data, status=status.HTTP_201_CREATED)


class ProductUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsStoreOwner]

    @extend_schema(
        tags=[_TAG],
        summary='Update product (owner only)',
        request=ProductSerializer,
        responses={200: ProductSerializer},
        examples=[
            OpenApiExample(
                'Update price and visibility',
                request_only=True,
                value={'base_price': '549.00', 'is_visible': True},
            ),
            OpenApiExample(
                'Mark product inactive',
                request_only=True,
                value={'status': 'inactive', 'is_visible': False},
            ),
        ],
    )
    def put(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, product)
        serializer = ProductSerializer(product, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        product = ProductService.update(product, serializer.validated_data)
        CacheService.invalidate_product_detail(str(product_id))
        return Response(ProductSerializer(product, context={'request': request}).data)

    @extend_schema(tags=[_TAG], summary='Delete product (owner only)', responses={204: None})
    def delete(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, product)
        product.delete()
        CacheService.invalidate_product_detail(str(product_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductWishlistView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=[_TAG], summary='Add / remove product from wishlist',
        request=None,
        responses={200: OpenApiResponse(response=inline_serializer('WishlistResponse', fields={
            'wishlisted': s.BooleanField(), 'message': s.CharField(),
        }))},
    )
    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, is_visible=True)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        added = ProductService.toggle_wishlist(request.user, product)
        msg = 'Added to wishlist.' if added else 'Removed from wishlist.'
        return Response({'wishlisted': added, 'message': msg})

    @extend_schema(tags=[_TAG], summary='Remove product from wishlist', responses={200: None})
    def delete(self, request, product_id):
        from apps.products.models import Wishlist
        Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
        return Response({'wishlisted': False, 'message': 'Removed from wishlist.'})


class ProductReserveView(APIView):
    """POST /products/<id>/reserve/ — create a reservation for this product."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Reserve a product',
        request=inline_serializer('ReserveBody', fields={
            'store_id': s.UUIDField(),
            'quantity': s.IntegerField(default=1),
            'note':     s.CharField(required=False, allow_blank=True),
        }),
        responses={201: OpenApiResponse(description='Reservation created')},
    )
    def post(self, request, product_id):
        from apps.stores.models import Store
        from apps.reservations.models import Reservation
        from apps.reservations.services import ReservationService
        from apps.blacklist.services import BlacklistService

        try:
            product = Product.objects.get(id=product_id, status='active', is_visible=True)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        store_id = request.data.get('store_id') or str(product.store_id)
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'customer' and BlacklistService.is_blocked(store, request.user):
            return Response({'error': 'blacklisted', 'message': 'You cannot reserve from this store.'}, status=status.HTTP_403_FORBIDDEN)

        quantity = int(request.data.get('quantity', 1))
        note     = request.data.get('note', '')
        reservation = ReservationService.create(
            customer=request.user, store=store, product=product, quantity=quantity, note=note,
        )
        from apps.reservations.serializers import ReservationSerializer
        return Response(ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)


class WishlistListView(APIView):
    """GET /api/v1/products/wishlist/ — return the authenticated user's saved products."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=[_TAG], summary='List wishlist products',
        responses={200: ProductListSerializer(many=True)},
    )
    def get(self, request):
        from apps.products.models import Wishlist
        product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
        products = Product.objects.filter(id__in=product_ids, is_visible=True)\
            .select_related('store').prefetch_related('variants', 'images')
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response({'results': serializer.data, 'count': len(serializer.data)})


class VendorProductListView(APIView):
    """GET /api/v1/products/vendor/ — return the authenticated vendor's own products."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='List my products (vendor only)',
        parameters=[
            OpenApiParameter('status', str, description='Filter by status (active/inactive)', required=False),
        ],
        responses={200: ProductSerializer(many=True)},
    )
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'results': [], 'count': 0})
        status_filter = request.query_params.get('status')
        qs = Product.objects.filter(store=request.user.store)\
            .select_related('store').prefetch_related('variants', 'images')\
            .order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = ProductSerializer(qs, many=True, context={'request': request})
        return Response({'results': serializer.data, 'count': len(serializer.data)})
