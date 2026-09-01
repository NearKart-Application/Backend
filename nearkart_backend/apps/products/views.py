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

from core.logging import log_event
from core.pagination import StandardOffsetPagination
from core.permissions import IsVendor, IsStoreOwner
from core.utils.vendor_log import log_vendor_action
from core.utils.customer_log import log_customer_action
from apps.billing.services import BillingService
from core.utils.cache import CacheService
from core.utils.upload_tracker import UploadTracker
from .models import Product, ProductVariant, ProductImage, StockWatchlist, StockMovementReason, ProductReview, ProductQA, ProductPriceHistory
from .serializers import (
    ProductSerializer, ProductListSerializer, MobileProductDetailSerializer,
    ProductReviewSerializer, ProductReviewListSerializer,
    ProductQASerializer, ProductPriceHistorySerializer,
)
from .services import ProductService
from .inventory_service import InventoryService, LOW_STOCK_THRESHOLD

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
            lat       = float(request.query_params['lat'])
            lng       = float(request.query_params['lng'])
            radius    = int(request.query_params.get('radius', 2))
            category  = request.query_params.get('category')
            store_id  = request.query_params.get('store')
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 100)
        except (KeyError, ValueError):
            return Response(
                {'error': 'validation_error', 'message': 'lat and lng are required numbers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        products = ProductService.get_nearby(lat, lng, radius_km=radius, category=category, store_id=store_id)
        total    = len(products)
        offset   = (page - 1) * page_size
        data     = ProductListSerializer(products[offset:offset + page_size], many=True, context={'request': request}).data
        return Response({
            'count':    total,
            'next':     page + 1 if offset + page_size < total else None,
            'previous': page - 1 if page > 1 else None,
            'results':  data,
        })


class ProductSearchView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Search products by name',
        parameters=[
            OpenApiParameter('q',          str,   description='Search query',                        required=True),
            OpenApiParameter('lat',        float, description='Latitude',                             required=False),
            OpenApiParameter('lng',        float, description='Longitude',                            required=False),
            OpenApiParameter('radius',     int,   description='Radius in km',                        required=False),
            OpenApiParameter('min_price',  float, description='Minimum price filter',                required=False),
            OpenApiParameter('max_price',  float, description='Maximum price filter',                required=False),
            OpenApiParameter('min_rating', float, description='Minimum store rating (0–5)',          required=False),
            OpenApiParameter('has_offer',  bool,  description='Only products with active offers',   required=False),
            OpenApiParameter('ordering',   str,   description='Sort: price_asc|price_desc|rating|distance', required=False),
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
        min_price  = request.query_params.get('min_price')
        max_price  = request.query_params.get('max_price')
        min_rating = request.query_params.get('min_rating')
        has_offer  = request.query_params.get('has_offer', '').lower() in ('1', 'true')
        ordering   = request.query_params.get('ordering')
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 50)
        except ValueError:
            page, page_size = 1, 20
        offset = (page - 1) * page_size
        products   = ProductService.search(
            query, lat, lng, radius,
            min_price=float(min_price) if min_price else None,
            max_price=float(max_price) if max_price else None,
            min_rating=float(min_rating) if min_rating else None,
            has_offer=has_offer or None,
            ordering=ordering,
            limit=offset + page_size + 1,
        )
        total      = len(products)
        page_data  = products[offset:offset + page_size]
        serialized = ProductListSerializer(page_data, many=True, context={'request': request}).data
        user = request.user if request.user.is_authenticated else None
        if page == 1:
            log_event('customers', action='product_searched', query=query, results=total,
                      user_id=str(user.id) if user else None)
            log_customer_action(request, 'search', entity_type='query',
                                entity_name=query, meta={'results': total, 'radius': radius})
        return Response({
            'count':    total,
            'next':     page + 1 if offset + page_size < total else None,
            'previous': page - 1 if page > 1 else None,
            'results':  serialized,
        })


class ProductAutocompleteView(APIView):
    """GET /products/autocomplete/?q= — product name + store name prefix suggestions (max 5)."""
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if len(q) < 2:
            return Response({'suggestions': []})
        from apps.stores.models import Store
        prod_names = list(
            Product.objects.filter(
                status='active', is_visible=True,
                store__is_active=True, store__is_verified=True,
                name__icontains=q,
            ).values_list('name', flat=True).distinct()[:5]
        )
        store_names = list(
            Store.objects.filter(is_active=True, is_verified=True, name__icontains=q)
            .values_list('name', flat=True).distinct()[:5]
        )
        seen: set = set()
        suggestions: list = []
        for item in prod_names + store_names:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                suggestions.append(item)
            if len(suggestions) >= 5:
                break
        return Response({'suggestions': suggestions})


class FollowingFeedView(APIView):
    """GET /api/v1/products/following/ — recent products from stores the user follows."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Products from followed stores',
        parameters=[
            OpenApiParameter('lat',       float, description='Latitude',                     required=False),
            OpenApiParameter('lng',       float, description='Longitude',                    required=False),
            OpenApiParameter('per_store', int,   description='Max products per store (default 3)', required=False),
        ],
        responses={200: ProductListSerializer(many=True)},
    )
    def get(self, request):
        from apps.stores.models import StoreFollow
        followed_ids = list(
            StoreFollow.objects.filter(user=request.user).values_list('store_id', flat=True)
        )
        products = (
            Product.objects
            .filter(store_id__in=followed_ids, status='active', is_visible=True)
            .select_related('store')
            .prefetch_related('variants', 'images')
            .order_by('-created_at')[:50]
        )
        serialized = ProductListSerializer(products, many=True, context={'request': request}).data
        return Response({'count': len(serialized), 'next': None, 'previous': None, 'results': serialized})


class RecommendedProductsView(APIView):
    """GET /api/v1/products/recommended/ — personalised products based on wishlist categories.
    Falls back to nearest products for unauthenticated or zero-wishlist users."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            lat    = float(request.query_params['lat'])
            lng    = float(request.query_params['lng'])
            radius = int(request.query_params.get('radius', 5))
        except (KeyError, ValueError):
            return Response(
                {'error': 'validation_error', 'message': 'lat and lng are required numbers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        categories: list[str] = []
        if request.user.is_authenticated:
            from .models import Wishlist
            categories = list(
                Wishlist.objects.filter(user=request.user)
                .values_list('product__category', flat=True)
                .distinct()[:5]
            )

        if categories:
            from core.utils.geo import get_nearby_products
            seen_ids: set = set()
            rec_products: list = []
            for cat in categories:
                for p in get_nearby_products(lat, lng, radius, category=cat, limit=10):
                    pid = str(p.id)
                    if pid not in seen_ids:
                        rec_products.append(p)
                        seen_ids.add(pid)
                    if len(rec_products) >= 20:
                        break
                if len(rec_products) >= 20:
                    break
        else:
            rec_products = ProductService.get_nearby(lat, lng, radius_km=radius, limit=20)

        data = ProductListSerializer(rec_products[:20], many=True, context={'request': request}).data
        return Response({'count': len(data), 'results': data})


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=[_TAG], summary='Get product detail', responses={200: ProductSerializer}, auth=[])
    def get(self, request, product_id):
        key    = CacheService.product_detail_key(str(product_id))
        cached = CacheService.get(key)
        if cached is not None:
            return Response(cached)
        try:
            from django.db.models import Avg, Count
            product = Product.objects.select_related('store').prefetch_related('variants', 'images').annotate(
                store_avg_rating=Avg('store__reviews__rating'),
                store_review_count=Count('store__reviews'),
            ).get(
                id=product_id, is_visible=True, status='active',
            )
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = MobileProductDetailSerializer(product, context={'request': request}).data
        CacheService.set(key, data, timeout=CacheService.TTL_PRODUCT_DETAIL)
        user = request.user if request.user.is_authenticated else None
        log_event('products', action='product_viewed', product_id=str(product_id),
                  store_id=str(product.store_id), user_id=str(user.id) if user else None)
        log_customer_action(request, 'product_view', entity_type='product',
                            entity_id=str(product_id), entity_name=product.name,
                            meta={'store_id': str(product.store_id), 'store_name': product.store.name})
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
                {'error': 'subscription_required', 'message': msg},
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
        log_event('products', action='product_created', product_id=str(product.id),
                  store_id=str(request.user.store.id), user_id=str(request.user.id),
                  name=product.name, price=str(product.base_price))
        log_vendor_action(request, 'product_create', entity_type='product',
                          entity_id=str(product.id), entity_name=product.name,
                          meta={'price': str(product.base_price), 'category': product.category})
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

        # If sale_price provided, apply it to the first variant (drives is_on_sale + discount %)
        sale_price_raw = request.data.get('sale_price')
        if sale_price_raw is not None:
            from decimal import Decimal, InvalidOperation
            try:
                sale_price = Decimal(str(sale_price_raw))
                variant = product.variants.order_by('created_at').first()
                if variant:
                    # Clear sale if sale_price >= base_price
                    variant.price = sale_price if sale_price < product.base_price else product.base_price
                    variant.save(update_fields=['price'])
            except (InvalidOperation, ValueError):
                pass

        CacheService.invalidate_product_detail(str(product_id))
        log_event('products', action='product_updated', product_id=str(product_id),
                  store_id=str(product.store_id), user_id=str(request.user.id))
        log_vendor_action(request, 'product_update', entity_type='product',
                          entity_id=str(product_id), entity_name=product.name,
                          meta={'fields': list(serializer.validated_data.keys())})
        return Response(ProductSerializer(product, context={'request': request}).data)

    @extend_schema(tags=[_TAG], summary='Delete product (owner only)', responses={204: None})
    def delete(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, product)
        store_id = str(product.store_id)
        product_name = product.name
        product.delete()
        CacheService.invalidate_product_detail(str(product_id))
        log_event('products', action='product_deleted', product_id=str(product_id),
                  store_id=store_id, user_id=str(request.user.id))
        log_vendor_action(request, 'product_delete', entity_type='product',
                          entity_id=str(product_id), entity_name=product_name)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImageUploadView(APIView):
    """POST /api/v1/products/<id>/images/ — upload up to 5 images for a product."""
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, product)

        files = request.FILES.getlist('images')
        if not files:
            return Response({'error': 'no_files', 'message': 'No images provided.'}, status=status.HTTP_400_BAD_REQUEST)

        existing_count = product.images.count()
        if existing_count + len(files) > 5:
            return Response(
                {'error': 'limit_exceeded', 'message': f'Max 5 images per product. You already have {existing_count}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── NF-27: Photo quality check ──────────────────────────────────────────
        try:
            from PIL import Image as PilImage
            import io
            MIN_DIM = 300
            MAX_SIZE_MB = 10
            for file in files:
                if file.size > MAX_SIZE_MB * 1024 * 1024:
                    return Response(
                        {'error': 'image_too_large', 'message': f'Each image must be under {MAX_SIZE_MB} MB.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                file.seek(0)
                img = PilImage.open(io.BytesIO(file.read()))
                w, h = img.size
                if w < MIN_DIM or h < MIN_DIM:
                    return Response(
                        {'error': 'image_too_small',
                         'message': f'Image "{file.name}" is {w}×{h} px. Minimum is {MIN_DIM}×{MIN_DIM} px.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                file.seek(0)
        except ImportError:
            pass  # Pillow not installed; skip check

        try:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            import uuid, os

            saved_urls = []
            for i, file in enumerate(files):
                ext = os.path.splitext(file.name)[1].lower() or '.jpg'
                filename = f'products/{product_id}/{uuid.uuid4().hex}{ext}'
                path = default_storage.save(filename, ContentFile(file.read()))
                raw_url = default_storage.url(path)
                if raw_url.startswith('http'):
                    url = raw_url.replace('http://', 'https://', 1)
                else:
                    url = request.build_absolute_uri(raw_url).replace('http://', 'https://', 1)
                is_primary = (existing_count == 0 and i == 0)
                ProductImage.objects.create(
                    product=product,
                    image_url=url,
                    is_primary=is_primary,
                    order=existing_count + i,
                )
                saved_urls.append(url)

            CacheService.invalidate_product_detail(str(product_id))
            log_vendor_action(request, 'image_upload', entity_type='product',
                              entity_id=str(product_id), entity_name=product.name,
                              meta={'count': len(saved_urls)})
            return Response({'urls': saved_urls, 'primary_image': saved_urls[0] if saved_urls else None})

        except Exception as e:
            logger.error('Product image upload failed: %s', e)
            return Response({'error': 'upload_failed', 'message': 'Image upload failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductImageDeleteView(APIView):
    """DELETE /api/v1/products/<id>/images/<image_id>/ — remove a single product image."""
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def delete(self, request, product_id, image_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, product)
        deleted, _ = ProductImage.objects.filter(id=image_id, product=product).delete()
        if not deleted:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        # If no primary left, promote the first remaining image
        if not product.images.filter(is_primary=True).exists():
            first = product.images.order_by('order').first()
            if first:
                first.is_primary = True
                first.save(update_fields=['is_primary'])
        CacheService.invalidate_product_detail(str(product_id))
        log_vendor_action(request, 'image_delete', entity_type='product',
                          entity_id=str(product_id), entity_name=product.name)
        remaining = [{'id': str(img.id), 'image_url': img.image_url, 'is_primary': img.is_primary}
                     for img in product.images.order_by('order')]
        return Response({'images': remaining})


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
        log_event('customers', action='product_wishlisted' if added else 'product_unwishlisted',
                  product_id=str(product_id), store_id=str(product.store_id),
                  user_id=str(request.user.id))
        log_customer_action(request, 'wishlist_add' if added else 'wishlist_remove',
                            entity_type='product', entity_id=str(product_id), entity_name=product.name)
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

        quantity         = int(request.data.get('quantity', 1))
        note             = request.data.get('note', '')
        points_to_redeem = int(request.data.get('points_to_redeem', 0))
        discount_amount  = 0

        if points_to_redeem > 0:
            try:
                from apps.loyalty.services import LoyaltyService
                discount_amount = LoyaltyService.redeem_points(
                    user=request.user,
                    points=points_to_redeem,
                    description=f'Discount on reservation — {product.name}',
                )
            except ValueError as e:
                return Response({'error': 'loyalty_error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        reservation = ReservationService.create(
            customer=request.user, store=store, product=product, quantity=quantity, note=note,
            points_redeemed=points_to_redeem, discount_amount=discount_amount,
        )
        log_customer_action(request, 'reservation_create', entity_type='product',
                            entity_id=str(product_id), entity_name=product.name,
                            meta={'store_id': str(store.id), 'store_name': store.name,
                                  'quantity': quantity, 'reservation_id': str(reservation.id)})
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


class GenerateProductCodeView(APIView):
    """GET /api/v1/products/vendor/generate-code/ — return a unique NKP code for a new product."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='Pre-generate a unique product code')
    def get(self, request):
        category = request.query_params.get('category', '')
        store = getattr(request.user, 'store', None)
        code = ProductService._generate_product_code(store=store, category=category)
        return Response({'product_code': code})


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
        from django.db.models import Exists, OuterRef, Value, BooleanField
        from .models import Wishlist
        status_filter = request.query_params.get('status')
        qs = (
            Product.objects
            .filter(store=request.user.store)
            .select_related('store')
            .prefetch_related('variants', 'images')
            .annotate(
                _is_wishlisted=Exists(
                    Wishlist.objects.filter(product=OuterRef('pk'), user=request.user)
                )
            )
            .order_by('-created_at')
        )
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = StandardOffsetPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProductSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


# ── Inventory Management ──────────────────────────────────────────────────────

class VariantListView(APIView):
    """GET /products/<id>/variants/ — list variants with stock for vendor."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='List variants with stock')
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, store=request.user.store)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=404)
        variants = product.variants.all()
        data = [
            {
                'id':             str(v.id),
                'name':           v.name,
                'sku':            v.sku,
                'price':          str(v.price),
                'stock_quantity': v.stock_quantity,
            }
            for v in variants
        ]
        return Response({'results': data, 'count': len(data)})


class VariantStockUpdateView(APIView):
    """PATCH /products/<id>/variants/<vid>/ — vendor updates stock qty."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='Update variant stock')
    def patch(self, request, product_id, variant_id):
        try:
            product = Product.objects.get(id=product_id, store=request.user.store)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=404)
        try:
            variant = product.variants.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Variant not found.'}, status=404)

        new_qty = request.data.get('stock_quantity')
        if new_qty is None or not isinstance(new_qty, int) or new_qty < 0:
            return Response({'error': 'validation_error', 'message': 'stock_quantity must be a non-negative integer.'}, status=400)

        note = request.data.get('note', '')
        old_qty = variant.stock_quantity
        InventoryService.update_stock(
            variant=variant, new_qty=new_qty,
            changed_by=request.user,
            reason=StockMovementReason.MANUAL,
            note=note,
        )
        log_vendor_action(request, 'stock_update', entity_type='variant',
                          entity_id=str(variant_id), entity_name=f'{product.name} / {variant.name}',
                          meta={'old_qty': old_qty, 'new_qty': new_qty, 'delta': new_qty - old_qty, 'note': note})
        return Response({
            'id':             str(variant.id),
            'name':           variant.name,
            'stock_quantity': variant.stock_quantity,
            'product_status': variant.product.status,
        })


class ProductVariantBulkUpdateView(APIView):
    """PATCH /products/<id>/variants/bulk/ — update price + stock for multiple variants at once."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='Bulk update variant price and stock')
    def patch(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, store=request.user.store)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=404)

        updates = request.data.get('variants')
        if not isinstance(updates, list) or not updates:
            return Response({'error': 'validation_error', 'message': 'variants must be a non-empty list.'}, status=400)

        variant_ids = [u.get('id') for u in updates if u.get('id')]
        variants_map = {str(v.id): v for v in product.variants.filter(id__in=variant_ids)}

        updated = []
        stock_changes = []  # (variant, old_qty, new_qty) for logging
        errors  = []
        for item in updates:
            vid = item.get('id')
            if not vid or vid not in variants_map:
                errors.append({'id': vid, 'error': 'not_found'})
                continue
            variant = variants_map[vid]
            changed = False
            if 'price' in item:
                from decimal import Decimal, InvalidOperation
                try:
                    variant.price = Decimal(str(item['price']))
                    changed = True
                except (InvalidOperation, ValueError):
                    errors.append({'id': vid, 'error': 'invalid_price'})
                    continue
            if 'stock_quantity' in item:
                qty = item['stock_quantity']
                if not isinstance(qty, int) or qty < 0:
                    errors.append({'id': vid, 'error': 'invalid_stock_quantity'})
                    continue
                old_qty = variant.stock_quantity
                variant.stock_quantity = qty
                changed = True
                stock_changes.append((variant, old_qty, qty))
            if changed:
                updated.append(variant)

        if updated:
            ProductVariant.objects.bulk_update(updated, ['price', 'stock_quantity'])
            # Log stock movements for variants where stock_quantity changed
            if stock_changes:
                from .models import StockMovementLog
                StockMovementLog.objects.bulk_create([
                    StockMovementLog(
                        variant=v,
                        old_qty=old_q,
                        new_qty=new_q,
                        delta=new_q - old_q,
                        reason=StockMovementReason.MANUAL,
                        changed_by=request.user,
                        note='bulk update',
                    )
                    for v, old_q, new_q in stock_changes
                ])

        if updated:
            log_vendor_action(request, 'stock_bulk_update', entity_type='product',
                              entity_id=str(product_id), entity_name=product.name,
                              meta={'updated': len(updated), 'stock_changes': len(stock_changes), 'errors': len(errors)})
        return Response({
            'updated': len(updated),
            'errors':  errors,
        })


class StockLogView(APIView):
    """GET /products/<id>/stock-log/ — vendor views stock movement history."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='Stock movement history for a product')
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, store=request.user.store)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=404)

        from .models import StockMovementLog
        logs = StockMovementLog.objects.filter(
            variant__product=product
        ).select_related('variant', 'changed_by').order_by('-created_at')[:100]

        data = [
            {
                'id':          str(log.id),
                'variant':     log.variant.name,
                'old_qty':     log.old_qty,
                'new_qty':     log.new_qty,
                'delta':       log.delta,
                'reason':      log.reason,
                'note':        log.note,
                'changed_by':  log.changed_by.phone_number if log.changed_by else 'system',
                'created_at':  log.created_at.isoformat(),
            }
            for log in logs
        ]
        return Response({'results': data, 'count': len(data)})


class VendorStockLogsView(APIView):
    """GET /products/vendor/stock-logs/ — paginated stock movement history across all vendor products."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='All stock movement logs (vendor-wide)',
        parameters=[
            OpenApiParameter('product_id', str,  description='Filter by product UUID',  required=False),
            OpenApiParameter('variant_id', str,  description='Filter by variant UUID',  required=False),
            OpenApiParameter('reason',     str,  description='Filter by reason (manual/reservation/restoration/restock/invoice)', required=False),
        ],
    )
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'results': [], 'count': 0})

        from .models import StockMovementLog
        qs = (
            StockMovementLog.objects
            .filter(variant__product__store=request.user.store)
            .select_related('variant', 'variant__product', 'changed_by')
            .order_by('-created_at')
        )

        product_id = request.query_params.get('product_id')
        if product_id:
            qs = qs.filter(variant__product__id=product_id)

        variant_id = request.query_params.get('variant_id')
        if variant_id:
            qs = qs.filter(variant__id=variant_id)

        reason = request.query_params.get('reason')
        if reason:
            qs = qs.filter(reason=reason)

        paginator = StandardOffsetPagination()
        paginator.page_size = 25
        page = paginator.paginate_queryset(qs, request)

        data = [
            {
                'id':           str(log.id),
                'product_id':   str(log.variant.product.id),
                'product_name': log.variant.product.name,
                'variant_id':   str(log.variant.id),
                'variant_name': log.variant.name,
                'sku':          log.variant.sku,
                'old_qty':      log.old_qty,
                'new_qty':      log.new_qty,
                'delta':        log.delta,
                'reason':       log.reason,
                'note':         log.note,
                'changed_by':   log.changed_by.phone_number if log.changed_by else 'system',
                'created_at':   log.created_at.isoformat(),
            }
            for log in page
        ]
        return paginator.get_paginated_response(data)


class StockAlertsView(APIView):
    """GET /products/vendor/stock-alerts/ — vendor sees low-stock products."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(tags=[_TAG], summary='Low stock alerts for vendor')
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'results': [], 'count': 0})

        from django.db.models import Min
        low_stock_products = (
            Product.objects
            .filter(store=request.user.store, status__in=['active', 'out_of_stock'])
            .prefetch_related('variants', 'images')
            .annotate(min_stock=Min('variants__stock_quantity'))
            .filter(min_stock__lte=LOW_STOCK_THRESHOLD)
            .order_by('min_stock')
        )

        data = []
        for p in low_stock_products:
            primary_image = next((img.image_url for img in p.images.all() if img.is_primary), None)
            low_variants = [
                {'id': str(v.id), 'name': v.name, 'stock_quantity': v.stock_quantity}
                for v in p.variants.all()
                if v.stock_quantity <= LOW_STOCK_THRESHOLD
            ]
            data.append({
                'id':            str(p.id),
                'product_code':  p.product_code,
                'name':          p.name,
                'status':        p.status,
                'primary_image': primary_image,
                'low_variants':  low_variants,
            })

        return Response({'results': data, 'count': len(data), 'threshold': LOW_STOCK_THRESHOLD})


class StockWatchView(APIView):
    """POST/DELETE /products/<id>/watch/ — customer subscribes/unsubscribes to back-in-stock."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=[_TAG], summary='Subscribe to back-in-stock notification')
    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, is_visible=True)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=404)

        if product.status != 'out_of_stock':
            return Response({'error': 'in_stock', 'message': 'Product is already in stock.'}, status=400)

        _, created = StockWatchlist.objects.get_or_create(customer=request.user, product=product)
        return Response({'watching': True, 'created': created}, status=201 if created else 200)

    @extend_schema(tags=[_TAG], summary='Unsubscribe from back-in-stock notification')
    def delete(self, request, product_id):
        deleted, _ = StockWatchlist.objects.filter(
            customer=request.user, product_id=product_id
        ).delete()
        return Response({'watching': False, 'deleted': deleted > 0})


class ProductReviewView(APIView):
    """
    GET  /products/<id>/reviews/  — list reviews (public)
    POST /products/<id>/reviews/  — create or update review (customer, verified purchase)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(tags=[_TAG], summary='List product reviews', auth=[])
    def get(self, request, product_id):
        from django.db.models import Avg
        try:
            product = Product.objects.get(id=product_id, status='active', is_visible=True)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        reviews_qs = product.reviews.select_related('reviewer').order_by('-created_at')
        total = reviews_qs.count()
        avg_rating = reviews_qs.aggregate(avg=Avg('rating'))['avg'] or 0.0
        reviews = reviews_qs[:50]
        data = {
            'results': ProductReviewListSerializer(reviews, many=True).data,
            'count':   total,
            'avg_rating': round(avg_rating, 1),
        }
        return Response(data)

    @extend_schema(tags=[_TAG], summary='Create or update a verified product review', request=ProductReviewSerializer)
    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Verify: customer's NS code must appear in an invoice for this product's store
        ns_code = request.user.profile_id or ''
        if not ns_code:
            return Response(
                {'error': 'no_ns_code', 'message': 'Your account has no NS code. Complete your profile first.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        from apps.stores.models import Invoice
        eligible_invoice = None
        invoices = Invoice.objects.filter(store=product.store, customer_ns_code=ns_code)
        for inv in invoices:
            for item in (inv.items or []):
                if str(item.get('product_id', '')).strip() == str(product.id):
                    eligible_invoice = inv
                    break
            if eligible_invoice:
                break

        if not eligible_invoice:
            return Response(
                {'error': 'not_eligible',
                 'message': 'You can only review a product you purchased from this store.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProductReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review, _ = ProductReview.objects.update_or_create(
            product=product, reviewer=request.user,
            defaults={
                'rating':  serializer.validated_data['rating'],
                'content': serializer.validated_data.get('content', ''),
                'invoice': eligible_invoice,
            },
        )
        # Notify vendor
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_new_review(
                product.store.owner,
                product.store.name,
                review.rating,
                str(product.store.id),
            )
        except Exception:
            pass
        return Response(ProductReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ProductDemoVideoView(APIView):
    """GET /products/<product_id>/demo-video/ — returns the latest ready product_demo video for a product."""
    permission_classes = [AllowAny]

    def get(self, request, product_id):
        from apps.videos.models import Video
        from apps.videos.serializers import VideoSerializer
        video = (
            Video.objects
            .filter(
                product_id=product_id,
                video_type=Video.TYPE_PRODUCT_DEMO,
                status=Video.STATUS_READY,
                is_visible=True,
            )
            .order_by('-created_at')
            .first()
        )
        if not video:
            return Response({'detail': 'No demo video found for this product.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(VideoSerializer(video, context={'request': request}).data)


class ProductQAView(APIView):
    """
    GET  /products/<id>/qa/   — list Q&A (public)
    POST /products/<id>/qa/   — ask a question (authenticated)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, product_id):
        qs = ProductQA.objects.filter(product_id=product_id).select_related('user').order_by('-created_at')[:50]
        return Response({'results': ProductQASerializer(qs, many=True).data, 'count': qs.count()})

    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, is_visible=True)
        except Product.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        question = request.data.get('question', '').strip()
        if not question:
            return Response({'error': 'validation_error', 'message': 'question is required.'}, status=status.HTTP_400_BAD_REQUEST)
        qa = ProductQA.objects.create(product=product, user=request.user, question=question)
        return Response(ProductQASerializer(qa).data, status=status.HTTP_201_CREATED)


class ProductQAAnswerView(APIView):
    """PUT /products/<product_id>/qa/<qa_id>/answer/ — vendor answers a question."""
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def put(self, request, product_id, qa_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, product)
        try:
            qa = ProductQA.objects.get(id=qa_id, product=product)
        except ProductQA.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        answer = request.data.get('answer', '').strip()
        if not answer:
            return Response({'error': 'validation_error', 'message': 'answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        qa.answer = answer
        qa.answered_at = timezone.now()
        qa.save(update_fields=['answer', 'answered_at'])
        return Response(ProductQASerializer(qa).data)


class ProductPriceHistoryView(APIView):
    """GET /products/<id>/price-history/ — public price change log."""
    permission_classes = [AllowAny]

    def get(self, request, product_id):
        try:
            product = Product.objects.only('id', 'base_price', 'name').get(id=product_id, is_visible=True)
        except Product.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        history = ProductPriceHistory.objects.filter(product=product).order_by('-created_at')[:24]
        return Response({
            'current_price': str(product.base_price),
            'history': ProductPriceHistorySerializer(history, many=True).data,
        })


class ProductBulkImportView(APIView):
    """POST /products/vendor/import-csv/ — bulk create products from CSV file."""
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request):
        import csv, io
        if not hasattr(request.user, 'store'):
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=status.HTTP_400_BAD_REQUEST)
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'no_file', 'message': 'CSV file is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            text = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(text))
        except Exception:
            return Response({'error': 'invalid_file', 'message': 'Could not parse CSV.'}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        errors = []
        for i, row in enumerate(reader, start=2):
            name = (row.get('name') or '').strip()
            if not name:
                errors.append({'row': i, 'message': 'name is required'})
                continue
            try:
                base_price_raw = row.get('base_price') or row.get('price') or '0'
                base_price = float(base_price_raw.replace(',', '').strip())
                if base_price <= 0:
                    raise ValueError('price must be > 0')
            except (ValueError, AttributeError):
                errors.append({'row': i, 'message': f'invalid base_price: {base_price_raw!r}'})
                continue
            from decimal import Decimal
            product = Product.objects.create(
                store=request.user.store,
                name=name,
                category=(row.get('category') or 'others').strip().lower(),
                description=(row.get('description') or '').strip(),
                base_price=Decimal(str(base_price)),
                barcode=(row.get('barcode') or row.get('ean') or '').strip(),
                status='draft',
                is_visible=False,
            )
            stock = int((row.get('stock') or '0').strip() or '0')
            sku = f'{product.product_code}-DEFAULT'
            ProductVariant.objects.create(
                product=product, name='Default',
                sku=sku, price=product.base_price, stock_quantity=stock,
            )
            created_count += 1

        return Response({'created': created_count, 'errors': errors},
                        status=status.HTTP_201_CREATED if created_count else status.HTTP_400_BAD_REQUEST)


class ProductBundleComponentsView(APIView):
    """
    GET  /products/<id>/bundle-components/   — list bundle components
    POST /products/<id>/bundle-components/   — add a component variant
    """
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        from apps.inventory.models import CompositeProduct
        components = CompositeProduct.objects.filter(bundle_product=product).select_related('component_variant__product')
        data = [
            {
                'id': str(c.id),
                'variant_id': str(c.component_variant.id),
                'variant_name': c.component_variant.name,
                'product_name': c.component_variant.product.name,
                'quantity': c.quantity,
            }
            for c in components
        ]
        return Response({'results': data, 'count': len(data)})

    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, product)
        variant_id = request.data.get('variant_id')
        quantity = int(request.data.get('quantity', 1))
        if not variant_id:
            return Response({'error': 'validation_error', 'message': 'variant_id required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            variant = ProductVariant.objects.get(id=variant_id, product__store=request.user.store)
        except ProductVariant.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Variant not found in your store.'}, status=status.HTTP_404_NOT_FOUND)
        from apps.inventory.models import CompositeProduct
        comp, _ = CompositeProduct.objects.update_or_create(
            bundle_product=product, component_variant=variant,
            defaults={'quantity': quantity},
        )
        return Response({
            'id': str(comp.id), 'variant_id': str(variant.id),
            'variant_name': variant.name, 'quantity': comp.quantity,
        }, status=status.HTTP_201_CREATED)


class ProductBundleComponentDeleteView(APIView):
    """DELETE /products/<id>/bundle-components/<comp_id>/"""
    permission_classes = [IsAuthenticated, IsStoreOwner]

    def delete(self, request, product_id, comp_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, product)
        from apps.inventory.models import CompositeProduct
        deleted, _ = CompositeProduct.objects.filter(id=comp_id, bundle_product=product).delete()
        if not deleted:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Jewelry Attributes (#139–#142) ────────────────────────────────────────────

JEWELRY_FIELDS = {'weight_grams', 'price_per_gram', 'purity', 'making_charges', 'hallmark_number'}


class JewelryAttributesView(APIView):
    """
    GET  /products/<product_id>/variants/<variant_id>/jewelry/
    PATCH /products/<product_id>/variants/<variant_id>/jewelry/
    Read or update jewelry-specific fields on a variant.
    """
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_variant(self, request, product_id, variant_id):
        try:
            product = Product.objects.get(id=product_id, store=request.user.store)
        except Product.DoesNotExist:
            return None, None
        try:
            return product, product.variants.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return None, None

    def get(self, request, product_id, variant_id):
        _, variant = self._get_variant(request, product_id, variant_id)
        if not variant:
            return Response({'error': 'not_found'}, status=404)
        return Response({
            'variant_id':      str(variant.id),
            'variant_name':    variant.name,
            'weight_grams':    str(variant.weight_grams) if variant.weight_grams is not None else None,
            'price_per_gram':  str(variant.price_per_gram) if variant.price_per_gram is not None else None,
            'purity':          variant.purity,
            'making_charges':  str(variant.making_charges) if variant.making_charges is not None else None,
            'hallmark_number': variant.hallmark_number,
        })

    def patch(self, request, product_id, variant_id):
        _, variant = self._get_variant(request, product_id, variant_id)
        if not variant:
            return Response({'error': 'not_found'}, status=404)

        data = {k: v for k, v in request.data.items() if k in JEWELRY_FIELDS}
        if not data:
            return Response({'error': 'No jewelry fields provided.'}, status=400)

        for field, value in data.items():
            setattr(variant, field, value if value not in ('', None) else None if field != 'purity' and field != 'hallmark_number' else '')
        variant.save(update_fields=list(data.keys()))

        return Response({
            'variant_id':      str(variant.id),
            'variant_name':    variant.name,
            'weight_grams':    str(variant.weight_grams) if variant.weight_grams is not None else None,
            'price_per_gram':  str(variant.price_per_gram) if variant.price_per_gram is not None else None,
            'purity':          variant.purity,
            'making_charges':  str(variant.making_charges) if variant.making_charges is not None else None,
            'hallmark_number': variant.hallmark_number,
        })


class JewelryProductListView(APIView):
    """
    GET /products/jewelry/
    Returns all variants with any jewelry attribute set, for the vendor's store.
    Used by the Jewelry Inventory management UI.
    """
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        from django.db.models import Q
        store = request.user.store
        variants = ProductVariant.objects.filter(
            product__store=store,
        ).filter(
            Q(weight_grams__isnull=False) |
            Q(price_per_gram__isnull=False) |
            Q(purity__gt='') |
            Q(making_charges__isnull=False) |
            Q(hallmark_number__gt=''),
        ).select_related('product')
        return Response([
            {
                'variant_id':      str(v.id),
                'variant_name':    v.name,
                'product_id':      str(v.product_id),
                'product_name':    v.product.name,
                'sku':             v.sku,
                'price':           str(v.price),
                'weight_grams':    str(v.weight_grams) if v.weight_grams is not None else None,
                'price_per_gram':  str(v.price_per_gram) if v.price_per_gram is not None else None,
                'purity':          v.purity,
                'making_charges':  str(v.making_charges) if v.making_charges is not None else None,
                'hallmark_number': v.hallmark_number,
            }
            for v in variants
        ])
