"""Nearspot — Inventory Views"""
import logging

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsVendor
from .models import (
    Supplier, PurchaseOrder, StockAudit, StockAuditStatus,
    CompositeProduct, SerialNumber, SerialNumberStatus,
    GroceryBatch, WastageRecord, PurchaseSource, UnitOfMeasure,
)
# StockMovementLog and StockWatchlist live in the products app (canonical tables)
from apps.products.models import StockMovementLog, StockWatchlist
from .serializers import (
    StockMovementLogSerializer, StockWatchlistSerializer,
    SupplierSerializer, PurchaseOrderSerializer, StockAuditSerializer,
    CompositeProductSerializer, SerialNumberSerializer,
    GroceryBatchSerializer, WastageRecordSerializer,
    PurchaseSourceSerializer, UnitOfMeasureSerializer,
)

logger = logging.getLogger(__name__)
_TAG = 'Inventory'


def _vendor_store(request):
    """Return the vendor's store or raise AttributeError."""
    return request.user.store


def _apply_po_stock(po, changed_by):
    """Add stock for every item in a PO when it is marked received."""
    from django.db import transaction as db_transaction
    from apps.inventory.services import InventoryService
    from apps.products.models import ProductVariant, StockMovementReason
    for item in po.items:
        variant_id = item.get('variant_id')
        qty = item.get('qty', 0)
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            continue
        if not variant_id or qty <= 0:
            continue
        try:
            with db_transaction.atomic():
                variant = ProductVariant.objects.select_for_update().get(pk=variant_id)
                InventoryService.update_stock(
                    variant=variant,
                    new_qty=variant.stock_quantity + qty,
                    changed_by=changed_by,
                    reason=StockMovementReason.RESTOCK,
                    note=f'po:{po.id}',
                )
        except ProductVariant.DoesNotExist:
            logger.warning('[inventory] PO %s receive: variant %s not found', po.id, variant_id)
        except Exception:
            logger.exception('[inventory] PO %s: failed to update stock for variant %s', po.id, variant_id)


class StockMovementLogView(APIView):
    """GET /inventory/movements/ — stock movement history for vendor's products."""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)

        variant_id = request.query_params.get('variant_id')
        qs = StockMovementLog.objects.filter(
            variant__product__store=store,
        ).select_related('variant', 'changed_by').order_by('-created_at')
        if variant_id:
            qs = qs.filter(variant_id=variant_id)

        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 30)), 1), 100)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)

        total   = qs.count()
        offset  = (page - 1) * page_size
        results = qs[offset: offset + page_size]
        return Response({
            'count':    total,
            'page':     page,
            'has_next': offset + page_size < total,
            'results':  StockMovementLogSerializer(results, many=True).data,
        })


class SupplierListView(APIView):
    """GET/POST /inventory/suppliers/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        qs = Supplier.objects.filter(store=store, is_active=True).order_by('name')
        return Response(SupplierSerializer(qs, many=True).data)

    def post(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        # Plan-gated: enforce supplier_limit
        try:
            plan = store.subscription.plan
            if plan.supplier_limit > 0:
                current_count = Supplier.objects.filter(store=store, is_active=True).count()
                if current_count >= plan.supplier_limit:
                    return Response({
                        'error': 'plan_limit_reached',
                        'message': f'Your plan allows up to {plan.supplier_limit} suppliers. Upgrade to add more.',
                        'limit': plan.supplier_limit,
                    }, status=403)
        except Exception:
            pass
        ser = SupplierSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        supplier = ser.save(store=store)
        return Response(SupplierSerializer(supplier).data, status=201)


class SupplierDetailView(APIView):
    """GET/PATCH/DELETE /inventory/suppliers/<id>/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get(self, request, supplier_id):
        try:
            store = _vendor_store(request)
        except Exception:
            return None, Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        try:
            supplier = Supplier.objects.get(id=supplier_id, store=store)
        except Supplier.DoesNotExist:
            return None, Response({'error': 'not_found', 'message': 'Supplier not found.'}, status=404)
        return supplier, None

    def get(self, request, supplier_id):
        supplier, err = self._get(request, supplier_id)
        if err:
            return err
        return Response(SupplierSerializer(supplier).data)

    def patch(self, request, supplier_id):
        supplier, err = self._get(request, supplier_id)
        if err:
            return err
        ser = SupplierSerializer(supplier, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        ser.save()
        return Response(ser.data)

    def delete(self, request, supplier_id):
        supplier, err = self._get(request, supplier_id)
        if err:
            return err
        supplier.is_active = False
        supplier.save(update_fields=['is_active', 'updated_at'])
        return Response(status=204)


class PurchaseOrderListView(APIView):
    """GET/POST /inventory/purchase-orders/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        qs = PurchaseOrder.objects.filter(store=store).select_related('supplier').order_by('-created_at')
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 50)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        total   = qs.count()
        offset  = (page - 1) * page_size
        results = qs[offset: offset + page_size]
        return Response({
            'count':    total,
            'page':     page,
            'has_next': offset + page_size < total,
            'results':  PurchaseOrderSerializer(results, many=True).data,
        })

    def post(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        # Plan-gated: enforce po_limit_monthly
        try:
            plan = store.subscription.plan
            if plan.po_limit_monthly > 0:
                from django.utils.timezone import now
                from django.db.models import Count
                month_start = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                monthly_count = PurchaseOrder.objects.filter(store=store, created_at__gte=month_start).count()
                if monthly_count >= plan.po_limit_monthly:
                    return Response({
                        'error': 'plan_limit_reached',
                        'message': f'Your plan allows {plan.po_limit_monthly} purchase orders per month. Upgrade to create more.',
                        'limit': plan.po_limit_monthly,
                    }, status=403)
        except Exception:
            pass
        ser = PurchaseOrderSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        po = ser.save(store=store)
        return Response(PurchaseOrderSerializer(po).data, status=201)


class PurchaseOrderDetailView(APIView):
    """GET/PATCH /inventory/purchase-orders/<id>/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get(self, request, po_id):
        try:
            store = _vendor_store(request)
        except Exception:
            return None, Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        try:
            po = PurchaseOrder.objects.get(id=po_id, store=store)
        except PurchaseOrder.DoesNotExist:
            return None, Response({'error': 'not_found', 'message': 'Purchase order not found.'}, status=404)
        return po, None

    def get(self, request, po_id):
        po, err = self._get(request, po_id)
        if err:
            return err
        return Response(PurchaseOrderSerializer(po).data)

    def patch(self, request, po_id):
        po, err = self._get(request, po_id)
        if err:
            return err
        ser = PurchaseOrderSerializer(po, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        po = ser.save()
        if po.status == 'received' and not po.received_at:
            po.received_at = timezone.now()
            po.save(update_fields=['received_at', 'updated_at'])
            _apply_po_stock(po, request.user)
        return Response(PurchaseOrderSerializer(po).data)


class StockAuditListView(APIView):
    """GET/POST /inventory/audits/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        qs = StockAudit.objects.filter(store=store).select_related('conducted_by').order_by('-created_at')
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 10)), 1), 30)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        total   = qs.count()
        offset  = (page - 1) * page_size
        results = qs[offset: offset + page_size]
        return Response({
            'count':    total,
            'page':     page,
            'has_next': offset + page_size < total,
            'results':  StockAuditSerializer(results, many=True).data,
        })

    def post(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        ser = StockAuditSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        audit = ser.save(store=store, conducted_by=request.user)
        return Response(StockAuditSerializer(audit).data, status=201)


class StockAuditDetailView(APIView):
    """GET/PATCH /inventory/audits/<id>/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get(self, request, audit_id):
        try:
            store = _vendor_store(request)
        except Exception:
            return None, Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        try:
            audit = StockAudit.objects.get(id=audit_id, store=store)
        except StockAudit.DoesNotExist:
            return None, Response({'error': 'not_found', 'message': 'Audit not found.'}, status=404)
        return audit, None

    def get(self, request, audit_id):
        audit, err = self._get(request, audit_id)
        if err:
            return err
        return Response(StockAuditSerializer(audit).data)

    def patch(self, request, audit_id):
        audit, err = self._get(request, audit_id)
        if err:
            return err
        if audit.status == StockAuditStatus.COMPLETED:
            return Response({'error': 'already_completed', 'message': 'Completed audits cannot be modified.'}, status=400)
        ser = StockAuditSerializer(audit, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        audit = ser.save()
        if audit.status == StockAuditStatus.COMPLETED and not audit.completed_at:
            audit.completed_at = timezone.now()
            audit.save(update_fields=['completed_at', 'updated_at'])
        return Response(StockAuditSerializer(audit).data)


class StockWatchlistView(APIView):
    """GET /inventory/watchlist/ — customer's back-in-stock watchlist."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = StockWatchlist.objects.filter(
            customer=request.user,
        ).select_related('product').order_by('-created_at')
        return Response(StockWatchlistSerializer(qs, many=True).data)


class CompositeProductListView(APIView):
    """GET/POST /inventory/bundles/ — bundle component definitions for vendor's products."""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        qs = CompositeProduct.objects.filter(
            bundle_product__store=store,
        ).select_related('bundle_product', 'component_variant').order_by('bundle_product__name')
        return Response(CompositeProductSerializer(qs, many=True).data)

    def post(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        ser = CompositeProductSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        bundle_product = ser.validated_data['bundle_product']
        if bundle_product.store_id != store.id:
            return Response({'error': 'forbidden', 'message': 'Product does not belong to your store.'}, status=403)
        comp = ser.save()
        return Response(CompositeProductSerializer(comp).data, status=201)


class CompositeProductDetailView(APIView):
    """GET/DELETE /inventory/bundles/<id>/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get(self, request, comp_id):
        try:
            store = _vendor_store(request)
        except Exception:
            return None, Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        try:
            comp = CompositeProduct.objects.select_related('bundle_product').get(pk=comp_id)
        except CompositeProduct.DoesNotExist:
            return None, Response({'error': 'not_found', 'message': 'Bundle component not found.'}, status=404)
        if comp.bundle_product.store_id != store.id:
            return None, Response({'error': 'forbidden', 'message': 'Not your product.'}, status=403)
        return comp, None

    def get(self, request, comp_id):
        comp, err = self._get(request, comp_id)
        if err:
            return err
        return Response(CompositeProductSerializer(comp).data)

    def delete(self, request, comp_id):
        comp, err = self._get(request, comp_id)
        if err:
            return err
        comp.delete()
        return Response(status=204)


class SerialNumberListView(APIView):
    """GET/POST /inventory/serial-numbers/ — serial number registry for vendor's variants."""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        variant_id = request.query_params.get('variant_id')
        status_filter = request.query_params.get('status')
        qs = SerialNumber.objects.filter(
            variant__product__store=store,
        ).select_related('variant').order_by('-created_at')
        if variant_id:
            qs = qs.filter(variant_id=variant_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        try:
            page      = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 30)), 1), 100)
        except (TypeError, ValueError):
            return Response({'error': 'invalid_param', 'message': 'page and page_size must be integers.'}, status=400)
        total   = qs.count()
        offset  = (page - 1) * page_size
        results = qs[offset: offset + page_size]
        return Response({
            'count':    total,
            'page':     page,
            'has_next': offset + page_size < total,
            'results':  SerialNumberSerializer(results, many=True).data,
        })

    def post(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        ser = SerialNumberSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        variant = ser.validated_data['variant']
        if variant.product.store_id != store.id:
            return Response({'error': 'forbidden', 'message': 'Variant does not belong to your store.'}, status=403)
        sn = ser.save()
        return Response(SerialNumberSerializer(sn).data, status=201)


class SerialNumberDetailView(APIView):
    """GET/PATCH /inventory/serial-numbers/<id>/"""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get(self, request, sn_id):
        try:
            store = _vendor_store(request)
        except Exception:
            return None, Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)
        try:
            sn = SerialNumber.objects.select_related('variant__product').get(pk=sn_id)
        except SerialNumber.DoesNotExist:
            return None, Response({'error': 'not_found', 'message': 'Serial number not found.'}, status=404)
        if sn.variant.product.store_id != store.id:
            return None, Response({'error': 'forbidden', 'message': 'Not your product.'}, status=403)
        return sn, None

    def get(self, request, sn_id):
        sn, err = self._get(request, sn_id)
        if err:
            return err
        return Response(SerialNumberSerializer(sn).data)

    def patch(self, request, sn_id):
        sn, err = self._get(request, sn_id)
        if err:
            return err
        ser = SerialNumberSerializer(sn, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        sn = ser.save()
        if sn.status == SerialNumberStatus.SOLD and not sn.sold_at:
            from django.utils import timezone
            sn.sold_at = timezone.now()
            sn.save(update_fields=['sold_at', 'updated_at'])
        return Response(SerialNumberSerializer(sn).data)


class BulkStockAdjustView(APIView):
    """POST /inventory/bulk-adjust/ — adjust stock for multiple variants in one request."""
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request):
        from django.db import transaction as db_transaction
        from apps.inventory.services import InventoryService
        from apps.products.models import ProductVariant, StockMovementReason

        try:
            store = _vendor_store(request)
        except AttributeError:
            return Response({'error': 'no_store'}, status=400)

        items = request.data.get('items', [])
        if not items or not isinstance(items, list):
            return Response({'error': 'items list required'}, status=400)

        results = []
        for item in items:
            variant_id = item.get('variant_id')
            delta = item.get('delta')
            note  = item.get('note', '')
            try:
                delta = int(delta)
            except (TypeError, ValueError):
                results.append({'variant_id': variant_id, 'status': 'error', 'message': 'Invalid delta'})
                continue
            try:
                with db_transaction.atomic():
                    variant = ProductVariant.objects.select_for_update().get(
                        id=variant_id, product__store=store
                    )
                    new_qty = max(0, variant.stock_quantity + delta)
                    InventoryService.update_stock(
                        variant=variant,
                        new_qty=new_qty,
                        changed_by=request.user,
                        reason=StockMovementReason.MANUAL,
                        note=note or 'bulk_adjust',
                    )
                    results.append({'variant_id': variant_id, 'status': 'ok', 'new_qty': new_qty})
            except ProductVariant.DoesNotExist:
                results.append({'variant_id': variant_id, 'status': 'error', 'message': 'Not found'})
            except Exception as exc:
                results.append({'variant_id': variant_id, 'status': 'error', 'message': str(exc)})

        return Response({'results': results})


class StockValuationView(APIView):
    """GET /inventory/valuation/ — total stock value per variant (qty × cost_price)."""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        from django.db.models import F, ExpressionWrapper, DecimalField, Sum
        from apps.products.models import ProductVariant

        try:
            store = _vendor_store(request)
        except AttributeError:
            return Response({'error': 'no_store'}, status=400)

        qs = (
            ProductVariant.objects
            .filter(product__store=store, product__status='active')
            .select_related('product')
            .annotate(
                total_value=ExpressionWrapper(
                    F('stock_quantity') * F('cost_price'),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )

        rows = []
        grand_total = 0
        for v in qs:
            val = float(v.total_value or 0)
            grand_total += val
            rows.append({
                'variant_id':   str(v.id),
                'product_name': v.product.name,
                'variant_name': v.name,
                'sku':          v.sku,
                'unit':         v.unit,
                'qty':          v.stock_quantity,
                'cost_price':   float(v.cost_price or 0),
                'total_value':  round(val, 2),
            })

        return Response({'grand_total': round(grand_total, 2), 'items': rows})


class InventoryExportView(APIView):
    """GET /inventory/export/ — download inventory snapshot as CSV."""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        import csv
        from django.http import StreamingHttpResponse
        from apps.products.models import ProductVariant

        try:
            store = _vendor_store(request)
        except AttributeError:
            return Response({'error': 'no_store'}, status=400)

        qs = (
            ProductVariant.objects
            .filter(product__store=store)
            .select_related('product')
            .order_by('product__name', 'name')
        )

        def rows():
            header = ['Product', 'Variant', 'SKU', 'Unit', 'Stock', 'Cost Price', 'MRP', 'Price', 'Low Stock Threshold']
            yield header
            for v in qs:
                yield [
                    v.product.name,
                    v.name,
                    v.sku,
                    v.unit,
                    v.stock_quantity,
                    str(v.cost_price or ''),
                    str(v.mrp or ''),
                    str(v.price),
                    v.low_stock_threshold,
                ]

        class Echo:
            def write(self, value):
                return value

        writer = csv.writer(Echo())
        response = StreamingHttpResponse(
            (writer.writerow(r) for r in rows()),
            content_type='text/csv',
        )
        response['Content-Disposition'] = 'attachment; filename="inventory_export.csv"'
        return response


class DeadStockView(APIView):
    """GET /inventory/dead-stock/?days=30 — variants with no outbound stock movement in N days."""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Max
        from apps.products.models import ProductVariant, StockMovementLog, StockMovementReason

        try:
            store = _vendor_store(request)
        except AttributeError:
            return Response({'error': 'no_store'}, status=400)

        try:
            days = int(request.query_params.get('days', 30))
        except ValueError:
            days = 30
        cutoff = timezone.now() - timedelta(days=days)

        outbound_reasons = [
            StockMovementReason.RESERVATION,
            StockMovementReason.INVOICE,
        ]

        active_variant_ids = set(
            StockMovementLog.objects
            .filter(
                variant__product__store=store,
                reason__in=outbound_reasons,
                created_at__gte=cutoff,
            )
            .values_list('variant_id', flat=True)
        )

        dead = (
            ProductVariant.objects
            .filter(product__store=store, stock_quantity__gt=0)
            .exclude(id__in=active_variant_ids)
            .select_related('product')
            .order_by('-stock_quantity')
        )

        return Response({
            'days': days,
            'count': dead.count(),
            'items': [
                {
                    'variant_id':   str(v.id),
                    'product_name': v.product.name,
                    'variant_name': v.name,
                    'sku':          v.sku,
                    'unit':         v.unit,
                    'qty':          v.stock_quantity,
                    'cost_price':   float(v.cost_price or 0),
                }
                for v in dead
            ],
        })


# ── Grocery / Perishable Inventory ────────────────────────────────────────────

class GroceryBatchListView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _vendor_store(request)
        qs = GroceryBatch.objects.filter(
            variant__product__store=store,
        ).select_related('variant__product').prefetch_related('wastage_records')

        zone = request.query_params.get('zone')
        if zone:
            qs = qs.filter(temperature_zone=zone)

        expired = request.query_params.get('expired')
        if expired == 'true':
            from datetime import date
            qs = qs.filter(expiry_date__lt=date.today())
        elif expired == 'false':
            from datetime import date
            qs = qs.exclude(expiry_date__lt=date.today())

        return Response(GroceryBatchSerializer(qs, many=True).data)

    def post(self, request):
        store = _vendor_store(request)
        ser = GroceryBatchSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        # Ensure variant belongs to this store
        variant = ser.validated_data['variant']
        if variant.product.store_id != store.id:
            return Response({'error': 'Variant not in your store.'}, status=403)
        batch = ser.save(remaining_qty=ser.validated_data['quantity'])
        return Response(GroceryBatchSerializer(batch).data, status=201)


class GroceryBatchDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_batch(self, request, batch_id):
        store = _vendor_store(request)
        try:
            return GroceryBatch.objects.select_related('variant__product').prefetch_related(
                'wastage_records'
            ).get(id=batch_id, variant__product__store=store)
        except GroceryBatch.DoesNotExist:
            return None

    def get(self, request, batch_id):
        batch = self._get_batch(request, batch_id)
        if not batch:
            return Response({'error': 'Not found.'}, status=404)
        return Response(GroceryBatchSerializer(batch).data)

    def patch(self, request, batch_id):
        batch = self._get_batch(request, batch_id)
        if not batch:
            return Response({'error': 'Not found.'}, status=404)
        ser = GroceryBatchSerializer(batch, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        batch = ser.save()
        return Response(GroceryBatchSerializer(batch).data)

    def delete(self, request, batch_id):
        batch = self._get_batch(request, batch_id)
        if not batch:
            return Response({'error': 'Not found.'}, status=404)
        batch.delete()
        return Response(status=204)


class WastageRecordView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, batch_id):
        store = _vendor_store(request)
        try:
            batch = GroceryBatch.objects.get(id=batch_id, variant__product__store=store)
        except GroceryBatch.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)

        ser = WastageRecordSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        qty = ser.validated_data['quantity']
        if qty > batch.remaining_qty:
            return Response({'error': 'Wastage quantity exceeds remaining stock.'}, status=400)

        record = ser.save(batch=batch, recorded_by=request.user)
        return Response(WastageRecordSerializer(record).data, status=201)


class NearExpiryAlertView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        from datetime import date, timedelta
        store = _vendor_store(request)
        days = int(request.query_params.get('days', 7))
        threshold = date.today() + timedelta(days=days)

        batches = GroceryBatch.objects.filter(
            variant__product__store=store,
            is_perishable=True,
            expiry_date__isnull=False,
            expiry_date__lte=threshold,
            expiry_date__gte=date.today(),
        ).select_related('variant__product').prefetch_related('wastage_records').order_by('expiry_date')

        return Response({
            'days_threshold': days,
            'count': batches.count(),
            'batches': GroceryBatchSerializer(batches, many=True).data,
        })


# ── Purchase Sources (#58) ────────────────────────────────────────────────────

class PurchaseSourceListView(APIView):
    """GET /inventory/purchase-sources/  — list active sources for vendor's store.
    POST /inventory/purchase-sources/    — create a new purchase source."""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store'}, status=400)
        qs = PurchaseSource.objects.filter(store=store, is_active=True).order_by('name')
        return Response(PurchaseSourceSerializer(qs, many=True).data)

    def post(self, request):
        try:
            store = _vendor_store(request)
        except Exception:
            return Response({'error': 'no_store'}, status=400)
        ser = PurchaseSourceSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        ser.save(store=store)
        return Response(ser.data, status=201)


class PurchaseSourceDetailView(APIView):
    """PATCH /inventory/purchase-sources/<ps_id>/  — update fields.
    DELETE /inventory/purchase-sources/<ps_id>/   — soft-delete (is_active=False)."""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_ps(self, request, ps_id):
        try:
            store = _vendor_store(request)
        except Exception:
            return None, Response({'error': 'no_store'}, status=400)
        try:
            ps = PurchaseSource.objects.get(pk=ps_id, store=store)
        except PurchaseSource.DoesNotExist:
            return None, Response({'error': 'not_found'}, status=404)
        return ps, None

    def patch(self, request, ps_id):
        ps, err = self._get_ps(request, ps_id)
        if err:
            return err
        ser = PurchaseSourceSerializer(ps, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        ser.save()
        return Response(ser.data)

    def delete(self, request, ps_id):
        ps, err = self._get_ps(request, ps_id)
        if err:
            return err
        ps.is_active = False
        ps.save(update_fields=['is_active'])
        return Response(status=204)


# ── Unit of Measure (#56) ─────────────────────────────────────────────────────

class UomListView(APIView):
    """GET /inventory/uom/    — list UoM catalog (public: returns all; vendor: scoped to vendor).
    POST /inventory/uom/   — create a new unit (vendor only)."""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        qs = UnitOfMeasure.objects.all().order_by('category', 'name')
        return Response(UnitOfMeasureSerializer(qs, many=True).data)

    def post(self, request):
        ser = UnitOfMeasureSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        ser.save()
        return Response(ser.data, status=201)


class UomDetailView(APIView):
    """PATCH /inventory/uom/<uom_id>/  — update a unit.
    DELETE /inventory/uom/<uom_id>/ — hard-delete (only non-base units)."""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_uom(self, uom_id):
        try:
            return UnitOfMeasure.objects.get(pk=uom_id), None
        except UnitOfMeasure.DoesNotExist:
            return None, Response({'error': 'not_found'}, status=404)

    def patch(self, request, uom_id):
        uom, err = self._get_uom(uom_id)
        if err:
            return err
        ser = UnitOfMeasureSerializer(uom, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        ser.save()
        return Response(ser.data)

    def delete(self, request, uom_id):
        uom, err = self._get_uom(uom_id)
        if err:
            return err
        if uom.is_base_unit:
            return Response({'error': 'cannot_delete_base_unit'}, status=400)
        uom.delete()
        return Response(status=204)
