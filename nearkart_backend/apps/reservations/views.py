"""
NearKart — Reservation Views
Customers create/cancel reservations. Vendors confirm/reject/complete them.
"""
import logging

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample

from core.logging import log_event
from core.permissions import IsVendor

MONTHLY_CANCEL_LIMIT = 10
CANCEL_PENALTY_POINTS = 5
from apps.stores.models import Store
from apps.products.models import Product
from apps.blacklist.services import BlacklistService
from .models import Reservation, ReservationStatus
from .services import ReservationService
from .serializers import (
    ReservationSerializer,
    ReservationCreateSerializer,
    ReservationStatusUpdateSerializer,
)

logger = logging.getLogger(__name__)
_TAG = 'Reservations'


class ReservationCreateView(APIView):
    """GET/POST /reservations/ — list reservations or create a new one."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='List reservations',
        description='Customers see their own reservations. Vendors see all reservations for their store.',
        responses={200: ReservationSerializer(many=True)},
    )
    def get(self, request):
        return ReservationListView().get(request)

    @extend_schema(
        tags=[_TAG],
        summary='Create reservation',
        description='Customer reserves a product at a store. Hold lasts 2 hours.',
        request=ReservationCreateSerializer,
        responses={201: ReservationSerializer},
        examples=[
            OpenApiExample(
                'Reserve 2 kurtas',
                value={
                    'store_id':   '{{store_id}}',
                    'product_id': '{{product_id}}',
                    'quantity':   2,
                    'note':       'Please keep ready by 6 PM',
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        ser = ReservationCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        data = ser.validated_data

        # Resolve store
        try:
            store = Store.objects.get(id=data['store_id'], is_active=True)
        except Store.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Store not found.'}, status=404)

        # Resolve product (must belong to the store and be active)
        try:
            product = Product.objects.get(
                id=data['product_id'], store=store, status='active', is_visible=True
            )
        except Product.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Product not found or not available.'}, status=404)

        # Resolve optional variant
        variant = None
        if data.get('variant_id'):
            from apps.products.models import ProductVariant
            try:
                variant = product.variants.get(id=data['variant_id'])
            except ProductVariant.DoesNotExist:
                return Response({'error': 'not_found', 'message': 'Variant not found.'}, status=404)
            if variant.stock_quantity < data['quantity']:
                return Response({'error': 'out_of_stock', 'message': 'Not enough stock for this variant.'}, status=400)

        # Blacklist check — blocked customers cannot reserve
        if request.user.role == 'customer' and BlacklistService.is_blocked(store, request.user):
            return Response({'error': 'blacklisted', 'message': 'You cannot reserve from this store.'}, status=403)

        # Loyalty points redemption (optional)
        points_to_redeem = data.get('points_to_redeem', 0)
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
                return Response({'error': 'loyalty_error', 'message': str(e)}, status=400)

        try:
            reservation = ReservationService.create(
                customer=request.user,
                store=store,
                product=product,
                variant=variant,
                quantity=data['quantity'],
                note=data.get('note', ''),
                points_redeemed=points_to_redeem,
                discount_amount=discount_amount,
                hold_hours=data.get('hours', 2),
                pickup_time=data.get('pickup_time'),
            )
        except ValueError as exc:
            if str(exc) == 'insufficient_stock':
                return Response({'error': 'out_of_stock', 'message': 'Not enough stock available.'}, status=400)
            raise
        log_event('reservations', action='reservation_created',
                  reservation_id=str(reservation.id), store_id=str(store.id),
                  product_id=str(product.id), customer_id=str(request.user.id),
                  quantity=data['quantity'])
        log_event('stores', action='reservation_received', store_id=str(store.id),
                  reservation_id=str(reservation.id), product_id=str(product.id),
                  customer_id=str(request.user.id))
        log_event('customers', action='reservation_created', customer_id=str(request.user.id),
                  reservation_id=str(reservation.id), store_id=str(store.id),
                  product_id=str(product.id))
        return Response(ReservationSerializer(reservation).data, status=201)


class ReservationListView(APIView):
    """GET /reservations/ — list reservations for the authenticated user."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='List reservations',
        description=(
            'Customers see their own reservations. '
            'Vendors see all reservations for their store.'
        ),
        responses={200: ReservationSerializer(many=True)},
    )
    def get(self, request):
        user = request.user
        if user.role == 'vendor':
            try:
                store = user.store
            except Exception:
                return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
            qs = ReservationService.get_for_store(store)
        elif user.role in ('admin', 'master_admin'):
            # Admins see all reservations; location-scoped admins filtered by assigned city
            qs = Reservation.objects.select_related('store', 'product', 'customer', 'variant', 'served_by', 'served_by__user').all()
            assigned_city = (getattr(user, 'admin_assigned_city', '') or '').strip()
            if assigned_city:
                cities = [c.strip() for c in assigned_city.split(',') if c.strip()]
                from django.db.models import Q
                city_q = Q()
                for city in cities:
                    city_q |= Q(store__city__icontains=city) | Q(store__locality__icontains=city)
                qs = qs.filter(city_q)
            # Admin-only filters: status and search
            status_param = request.query_params.get('status')
            if status_param:
                qs = qs.filter(status=status_param)
            search_param = request.query_params.get('search', '').strip()
            if search_param:
                from django.db.models import Q as DQ
                qs = qs.filter(
                    DQ(store__name__icontains=search_param) |
                    DQ(customer__full_name__icontains=search_param) |
                    DQ(customer__phone_number__icontains=search_param)
                )
        else:
            qs = ReservationService.get_for_customer(user)

        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 100)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        total     = qs.count()
        offset    = (page - 1) * page_size
        results   = qs[offset: offset + page_size]
        return Response({
            'count':    total,
            'page':     page,
            'has_next': offset + page_size < total,
            'results':  ReservationSerializer(results, many=True).data,
        })


class ReservationDetailView(APIView):
    """GET /reservations/<id>/ — detail view (customer or store vendor only)."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Reservation detail',
        responses={200: ReservationSerializer},
    )
    def get(self, request, reservation_id):
        reservation = self._get_reservation(request.user, reservation_id)
        if reservation is None:
            return Response({'error': 'not_found', 'message': 'Reservation not found.'}, status=404)
        return Response(ReservationSerializer(reservation).data)

    def _get_reservation(self, user, reservation_id):
        try:
            r = Reservation.objects.select_related('store', 'product', 'customer', 'variant', 'served_by', 'served_by__user').get(id=reservation_id)
        except Reservation.DoesNotExist:
            return None
        if user.role == 'vendor':
            try:
                if r.store.owner_id != user.id:
                    return None
            except Exception:
                return None
        elif user.role in ('admin', 'master_admin'):
            pass  # admins can access any reservation
        else:
            if r.customer_id != user.id:
                return None
        return r


class ReservationStatusView(APIView):
    """PATCH /reservations/<id>/status/ — vendor updates status."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Update reservation status (vendor)',
        description='Vendor can confirm, cancel, or mark a reservation as completed.',
        request=ReservationStatusUpdateSerializer,
        responses={200: ReservationSerializer},
        examples=[
            OpenApiExample('Confirm', value={'status': 'confirmed', 'vendor_note': 'Ready for pickup!'}, request_only=True),
            OpenApiExample('Cancel',  value={'status': 'cancelled', 'vendor_note': 'Out of stock, sorry.'}, request_only=True),
            OpenApiExample('Complete', value={'status': 'completed'}, request_only=True),
        ],
    )
    def patch(self, request, reservation_id):
        try:
            store = request.user.store
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)

        try:
            reservation = Reservation.objects.select_related('store', 'product', 'customer').get(
                id=reservation_id, store=store
            )
        except Reservation.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Reservation not found.'}, status=404)

        ser = ReservationStatusUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        new_status  = ser.validated_data['status']
        vendor_note = ser.validated_data.get('vendor_note', '')

        if new_status == ReservationStatus.CANCELLED and not vendor_note.strip():
            return Response(
                {'error': 'note_required', 'message': 'A reason is required when cancelling a reservation.'},
                status=400,
            )

        # Only pending reservations can be confirmed
        if new_status == ReservationStatus.CONFIRMED:
            if reservation.status != ReservationStatus.PENDING:
                return Response(
                    {'error': 'invalid_status', 'message': 'Only pending reservations can be confirmed.'},
                    status=400,
                )

        # Pending OR confirmed reservations can be cancelled
        # (confirmed = vendor emergency-cancels after already confirming)
        if new_status == ReservationStatus.CANCELLED:
            if reservation.status not in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
                return Response(
                    {'error': 'invalid_status', 'message': f'Cannot cancel a {reservation.status} reservation.'},
                    status=400,
                )

        # Only confirmed reservations can be completed
        if new_status == ReservationStatus.COMPLETED:
            if reservation.status != ReservationStatus.CONFIRMED:
                return Response(
                    {'error': 'invalid_status', 'message': 'Only confirmed reservations can be marked completed.'},
                    status=400,
                )

        if new_status == ReservationStatus.CONFIRMED:
            reservation = ReservationService.confirm(reservation, vendor_note)
        elif new_status == ReservationStatus.CANCELLED:
            reservation = ReservationService.cancel(reservation, note=vendor_note, cancelled_by='vendor')
        elif new_status == ReservationStatus.COMPLETED:
            selling_price  = ser.validated_data.get('actual_selling_price')
            payment_method = ser.validated_data.get('payment_method', '')
            served_by_id   = ser.validated_data.get('served_by_id')
            reservation = ReservationService.complete(reservation, actual_selling_price=selling_price)
            update_fields = []
            if payment_method:
                reservation.payment_method = payment_method
                update_fields.append('payment_method')
            if served_by_id:
                try:
                    from apps.stores.models import StaffMember
                    reservation.served_by = StaffMember.objects.get(id=served_by_id, store=store)
                    update_fields.append('served_by')
                except StaffMember.DoesNotExist:
                    pass
            if update_fields:
                reservation.save(update_fields=update_fields)
            try:
                from apps.loyalty.services import LoyaltyService
                LoyaltyService.award_pickup_bonus(
                    user=reservation.customer,
                    description=f'Pickup bonus — {reservation.product.name}',
                )
                # Earn points on spend (1 pt per ₹1 spent)
                price = float(selling_price or reservation.product.base_price or 0)
                if price > 0:
                    LoyaltyService.award_purchase_points(
                        user=reservation.customer,
                        amount_rupees=price,
                        store=reservation.store,
                        description=f'Purchase reward — {reservation.product.name}',
                    )
            except Exception:
                logger.exception('[reservations] loyalty award failed for reservation %s', reservation.id)

        log_event('reservations', action=f'reservation_{new_status}',
                  reservation_id=str(reservation.id), store_id=str(store.id),
                  product_id=str(reservation.product_id),
                  customer_id=str(reservation.customer_id),
                  vendor_id=str(request.user.id), vendor_note=vendor_note)
        log_event('stores', action=f'reservation_{new_status}', store_id=str(store.id),
                  reservation_id=str(reservation.id), vendor_id=str(request.user.id))
        return Response(ReservationSerializer(reservation).data)


class ReservationCancelView(APIView):
    """POST /reservations/<id>/cancel/ — customer cancels their own pending reservation."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Cancel reservation (customer)',
        description='Customer can cancel only their own pending reservation.',
        request=None,
        responses={200: ReservationSerializer},
    )
    def post(self, request, reservation_id):
        try:
            reservation = Reservation.objects.select_related('store', 'product', 'customer').get(
                id=reservation_id, customer=request.user
            )
        except Reservation.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Reservation not found.'}, status=404)

        if reservation.status != ReservationStatus.PENDING:
            return Response(
                {'error': 'invalid_status', 'message': f'Cannot cancel a {reservation.status} reservation.'},
                status=400,
            )

        # Monthly cancellation limit check
        now = timezone.now()
        monthly_cancels = Reservation.objects.filter(
            customer=request.user,
            status=ReservationStatus.CANCELLED,
            cancelled_by='customer',
            updated_at__year=now.year,
            updated_at__month=now.month,
        ).count()
        if monthly_cancels >= MONTHLY_CANCEL_LIMIT:
            return Response(
                {
                    'error': 'cancel_limit_reached',
                    'message': f'You have reached your monthly cancellation limit ({MONTHLY_CANCEL_LIMIT}). This resets on the 1st of next month.',
                },
                status=400,
            )

        cancel_reason = request.data.get('cancel_reason', '') if request.data else ''
        reservation = ReservationService.cancel(reservation, cancel_reason=cancel_reason, cancelled_by='customer')

        # Deduct loyalty points penalty (silent — never blocks the cancel)
        try:
            from apps.loyalty.services import LoyaltyService
            LoyaltyService.deduct_cancellation_penalty(
                user=request.user,
                points=CANCEL_PENALTY_POINTS,
                description=f'Cancellation penalty — {reservation.product.name}',
            )
        except Exception:
            logger.exception('[reservations] deduct_cancellation_penalty failed for reservation %s', reservation.id)

        log_event('reservations', action='reservation_cancelled_by_customer',
                  reservation_id=str(reservation_id), store_id=str(reservation.store_id),
                  product_id=str(reservation.product_id), customer_id=str(request.user.id))
        log_event('customers', action='reservation_cancelled', customer_id=str(request.user.id),
                  reservation_id=str(reservation_id), store_id=str(reservation.store_id))
        return Response(ReservationSerializer(reservation).data)


class ReservationCartView(APIView):
    """POST /reservations/cart/ — create multiple reservations (cart checkout)."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Cart checkout — reserve multiple products',
        description='Atomically creates one reservation per cart item. Partial failures are reported.',
    )
    def post(self, request):
        items = request.data.get('items', [])
        if not items or not isinstance(items, list):
            return Response({'error': 'invalid_body', 'message': 'items must be a non-empty list.'}, status=400)
        if len(items) > 10:
            return Response({'error': 'too_many', 'message': 'Cart is limited to 10 items.'}, status=400)

        created   = []
        errors    = []

        for idx, item in enumerate(items):
            ser = ReservationCreateSerializer(data=item)
            if not ser.is_valid():
                errors.append({'index': idx, 'error': ser.errors})
                continue

            data = ser.validated_data
            try:
                store = Store.objects.get(id=data['store_id'], is_active=True)
            except Store.DoesNotExist:
                errors.append({'index': idx, 'error': 'Store not found.'}); continue
            try:
                product = Product.objects.get(id=data['product_id'], store=store, status='active', is_visible=True)
            except Product.DoesNotExist:
                errors.append({'index': idx, 'error': 'Product not found or unavailable.'}); continue

            from apps.blacklist.services import BlacklistService
            if BlacklistService.is_blocked(store, request.user):
                errors.append({'index': idx, 'error': 'You are blocked from this store.'}); continue

            variant = None
            if data.get('variant_id'):
                from apps.products.models import ProductVariant
                try:
                    variant = product.variants.get(id=data['variant_id'])
                except ProductVariant.DoesNotExist:
                    errors.append({'index': idx, 'error': 'Variant not found.'}); continue

            try:
                reservation = ReservationService.create(
                    customer=request.user,
                    store=store,
                    product=product,
                    variant=variant,
                    quantity=data['quantity'],
                    note=data.get('note', ''),
                    hold_hours=data.get('hours', 2),
                    pickup_time=data.get('pickup_time'),
                )
                created.append(ReservationSerializer(reservation).data)
            except ValueError as e:
                errors.append({'index': idx, 'error': str(e)})

        status_code = 201 if created else 400
        return Response({'created': created, 'errors': errors, 'count': len(created)}, status=status_code)


class ReservationReceiptView(APIView):
    """GET /reservations/<id>/receipt/ — structured receipt for completed reservations."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Download reservation receipt',
        description='Returns structured receipt data. Available for completed/cancelled reservations.',
    )
    def get(self, request, reservation_id):
        try:
            reservation = Reservation.objects.select_related('store', 'product', 'customer', 'variant').get(
                id=reservation_id
            )
        except Reservation.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Reservation not found.'}, status=404)

        if reservation.customer_id != request.user.id and request.user.role not in ('vendor', 'admin', 'master_admin'):
            return Response({'error': 'forbidden'}, status=403)

        product  = reservation.product
        store    = reservation.store
        customer = reservation.customer
        base_price = float(product.base_price) if hasattr(product, 'base_price') else 0.0
        quantity   = reservation.quantity
        subtotal   = base_price * quantity
        discount   = float(reservation.discount_amount or 0)
        total      = subtotal - discount

        receipt = {
            'receipt_number': f'NRS-{str(reservation.id).upper()[:8]}',
            'status':         reservation.status,
            'created_at':     reservation.created_at.isoformat(),
            'pickup_time':    reservation.pickup_time.isoformat() if reservation.pickup_time else None,
            'store': {
                'name':     store.name,
                'address':  getattr(store, 'address', ''),
                'locality': store.locality,
                'phone':    store.phone,
            },
            'customer': {
                'name':  customer.full_name or '',
                'phone': customer.phone_number or '',
            },
            'items': [{
                'name':       product.name,
                'variant':    reservation.variant.name if reservation.variant_id else '',
                'quantity':   quantity,
                'unit_price': base_price,
                'total':      base_price * quantity,
            }],
            'subtotal':       subtotal,
            'discount':       discount,
            'points_redeemed': reservation.points_redeemed,
            'total':          total,
            'note':           reservation.note,
            'vendor_note':    reservation.vendor_note,
        }
        return Response(receipt)


class ReservationWaitlistView(APIView):
    """POST /reservations/waitlist/ — join stock watchlist when a product is out of stock."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Join out-of-stock waitlist',
        description='Adds the product to the customer\'s stock watchlist so they are notified when it\'s back.',
    )
    def post(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'product_id required.'}, status=400)
        try:
            product = Product.objects.get(id=product_id)
        except (Product.DoesNotExist, Exception):
            return Response({'error': 'not_found', 'message': 'Product not found.'}, status=404)

        try:
            from apps.products.models import StockWatchlist
            obj, created = StockWatchlist.objects.get_or_create(
                user=request.user,
                product=product,
            )
        except Exception as e:
            return Response({'error': str(e)}, status=400)

        return Response({
            'joined':       created,
            'product_name': product.name,
            'message':      'You\'ll be notified when this product is back in stock.' if created else 'Already on waitlist.',
        }, status=201 if created else 200)


class ReservationReturnView(APIView):
    """POST /reservations/<id>/return/ — vendor marks item returned, restores stock."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Mark reservation as returned (vendor)',
        description='Sets status to cancelled and restores stock for the returned item.',
    )
    def post(self, request, reservation_id):
        from django.db import transaction as db_transaction
        from apps.inventory.services import InventoryService
        from apps.products.models import ProductVariant, StockMovementReason

        try:
            store = request.user.store
        except AttributeError:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)

        try:
            reservation = Reservation.objects.select_related('variant').get(
                id=reservation_id, store=store,
            )
        except Reservation.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Reservation not found.'}, status=404)

        if reservation.status not in ('confirmed', 'completed'):
            return Response({
                'error': 'invalid_status',
                'message': 'Only confirmed or completed reservations can be returned.',
            }, status=400)

        note = request.data.get('note', '')
        with db_transaction.atomic():
            reservation.status = ReservationStatus.CANCELLED
            reservation.vendor_note = note or reservation.vendor_note
            reservation.save(update_fields=['status', 'vendor_note', 'updated_at'])

            if reservation.variant_id:
                try:
                    variant = ProductVariant.objects.select_for_update().get(id=reservation.variant_id)
                    InventoryService.update_stock(
                        variant=variant,
                        new_qty=variant.stock_quantity + reservation.quantity,
                        changed_by=request.user,
                        reason=StockMovementReason.RETURN_FROM_CUSTOMER,
                        note=f'return:{reservation.id}',
                    )
                except ProductVariant.DoesNotExist:
                    pass

        return Response({'status': 'returned', 'reservation_id': str(reservation.id)})
