"""Nearspot — Inventory Views"""
import logging

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsVendor
from .models import (
    StockMovementLog, StockWatchlist,
    Supplier, PurchaseOrder, StockAudit, StockAuditStatus,
)
from .serializers import (
    StockMovementLogSerializer, StockWatchlistSerializer,
    SupplierSerializer, PurchaseOrderSerializer, StockAuditSerializer,
)

logger = logging.getLogger(__name__)
_TAG = 'Inventory'


def _vendor_store(request):
    """Return the vendor's store or raise AttributeError."""
    return request.user.store


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
