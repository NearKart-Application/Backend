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
from core.permissions import IsVendor, IsStoreOwner
from apps.billing.services import BillingService
from core.utils.cache import CacheService
from core.utils.upload_tracker import UploadTracker
from .models import Product, ProductVariant, ProductImage, StockWatchlist, StockMovementReason, ProductReview
from .serializers import ProductSerializer, ProductListSerializer, MobileProductDetailSerializer, ProductReviewSerializer, ProductReviewListSerializer
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
        products   = ProductService.search(
            query, lat, lng, radius,
            min_price=float(min_price) if min_price else None,
            max_price=float(max_price) if max_price else None,
            min_rating=float(min_rating) if min_rating else None,
            has_offer=has_offer or None,
            ordering=ordering,
        )
        serialized = ProductListSerializer(products, many=True, context={'request': request}).data
        user = request.user if request.user.is_authenticated else None
        log_event('customers', action='product_searched', query=query, results=len(serialized),
                  user_id=str(user.id) if user else None)
        return Response({'count': len(serialized), 'next': None, 'previous': None, 'results': serialized})


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
        per_store = int(request.query_params.get('per_store', 3))
        followed_ids = StoreFollow.objects.filter(user=request.user).values_list('store_id', flat=True)
        results = []
        for store_id in followed_ids:
            store_products = list(
                Product.objects.filter(
                    store_id=store_id,
                    status='active',
                    is_visible=True,
                ).select_related('store').prefetch_related('variants', 'images').order_by('-created_at')[:per_store]
            )
            results.extend(store_products)
        results.sort(key=lambda p: p.created_at, reverse=True)
        serialized = ProductListSerializer(results, many=True, context={'request': request}).data
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
        user = request.user if request.user.is_authenticated else None
        log_event('products', action='product_viewed', product_id=str(product_id),
                  store_id=str(product.store_id), user_id=str(user.id) if user else None)
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
        return Response(ProductSerializer(product, context={'request': request}).data)

    @extend_schema(tags=[_TAG], summary='Delete product (owner only)', responses={204: None})
    def delete(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, product)
        store_id = str(product.store_id)
        product.delete()
        CacheService.invalidate_product_detail(str(product_id))
        log_event('products', action='product_deleted', product_id=str(product_id),
                  store_id=store_id, user_id=str(request.user.id))
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
                url = raw_url if raw_url.startswith('http') else request.build_absolute_uri(raw_url)
                is_primary = (existing_count == 0 and i == 0)
                ProductImage.objects.create(
                    product=product,
                    image_url=url,
                    is_primary=is_primary,
                    order=existing_count + i,
                )
                saved_urls.append(url)

            CacheService.invalidate_product_detail(str(product_id))
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
        status_filter = request.query_params.get('status')
        qs = Product.objects.filter(store=request.user.store)\
            .select_related('store').prefetch_related('variants', 'images')\
            .order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = ProductSerializer(qs, many=True, context={'request': request})
        return Response({'results': serializer.data, 'count': len(serializer.data)})


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
        InventoryService.update_stock(
            variant=variant, new_qty=new_qty,
            changed_by=request.user,
            reason=StockMovementReason.MANUAL,
            note=note,
        )
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
                variant.stock_quantity = qty
                changed = True
            if changed:
                updated.append(variant)

        if updated:
            ProductVariant.objects.bulk_update(updated, ['price', 'stock_quantity'])

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
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        reviews = product.reviews.select_related('reviewer').order_by('-created_at')[:50]
        data = {
            'results': ProductReviewListSerializer(reviews, many=True).data,
            'count':   reviews.count(),
            'avg_rating': round(
                sum(r.rating for r in reviews) / len(reviews) if reviews else 0, 1
            ),
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
                request.user.full_name or request.user.phone_number,
                review.rating,
                product.store.name,
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
