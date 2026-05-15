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
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiResponse, inline_serializer
import rest_framework.serializers as s

from core.permissions import IsVendor, IsStoreOwner
from .models import Product
from .serializers import ProductSerializer, ProductListSerializer
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
        except (KeyError, ValueError):
            return Response(
                {'error': 'validation_error', 'message': 'lat and lng are required numbers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        products = ProductService.get_nearby(lat, lng, radius_km=radius, category=category)
        return Response(ProductListSerializer(products, many=True, context={'request': request}).data)


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
        return Response(ProductListSerializer(products, many=True, context={'request': request}).data)


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=[_TAG], summary='Get product detail', responses={200: ProductSerializer}, auth=[])
    def get(self, request, product_id):
        try:
            product = Product.objects.prefetch_related('variants', 'images').get(
                id=product_id, is_visible=True, status='active',
            )
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductSerializer(product, context={'request': request}).data)


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
        return Response(ProductSerializer(product, context={'request': request}).data)

    @extend_schema(tags=[_TAG], summary='Delete product (owner only)', responses={204: None})
    def delete(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, product)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductWishlistView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Add / remove product from wishlist',
        request=None,
        responses={200: OpenApiResponse(
            response=inline_serializer('WishlistResponse', fields={
                'wishlisted': s.BooleanField(),
                'message': s.CharField(),
            })
        )},
    )
    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, is_visible=True)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        added = ProductService.toggle_wishlist(request.user, product)
        msg = 'Added to wishlist.' if added else 'Removed from wishlist.'
        return Response({'wishlisted': added, 'message': msg})
