from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsVendor
from .models import Consumable, ServiceConsumable, Equipment, MaintenanceRecord, Resource, ResourceAllocation
from .serializers import (
    ConsumableSerializer, ServiceConsumableSerializer,
    EquipmentSerializer, MaintenanceRecordSerializer,
    ResourceSerializer, ResourceAllocationSerializer,
)


def _store(request):
    return request.user.store


# ── Consumables (#147) ────────────────────────────────────────────────────────

class ConsumableListView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        qs = Consumable.objects.filter(store=_store(request))
        if request.query_params.get('low_stock') == 'true':
            from django.db.models import F
            qs = qs.filter(current_stock__lte=F('reorder_level'))
        return Response(ConsumableSerializer(qs, many=True).data)

    def post(self, request):
        s = ConsumableSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(store=_store(request))
        return Response(s.data, status=201)


class ConsumableDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def _get(self, request, consumable_id):
        try:
            return Consumable.objects.get(id=consumable_id, store=_store(request))
        except Consumable.DoesNotExist:
            return None

    def get(self, request, consumable_id):
        obj = self._get(request, consumable_id)
        if not obj:
            return Response({'error': 'not_found'}, status=404)
        return Response(ConsumableSerializer(obj).data)

    def patch(self, request, consumable_id):
        obj = self._get(request, consumable_id)
        if not obj:
            return Response({'error': 'not_found'}, status=404)
        s = ConsumableSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def delete(self, request, consumable_id):
        obj = self._get(request, consumable_id)
        if not obj:
            return Response({'error': 'not_found'}, status=404)
        obj.delete()
        return Response(status=204)


# ── Service ↔ Consumable links (#148) ─────────────────────────────────────────

class ServiceConsumableListView(APIView):
    """GET/POST consumables linked to a service catalogue item."""
    permission_classes = [IsAuthenticated, IsVendor]

    def _check_service(self, request, service_id):
        from apps.stores.models import ServiceCatalogue
        try:
            return ServiceCatalogue.objects.get(id=service_id, store=_store(request))
        except ServiceCatalogue.DoesNotExist:
            return None

    def get(self, request, service_id):
        if not self._check_service(request, service_id):
            return Response({'error': 'not_found'}, status=404)
        qs = ServiceConsumable.objects.filter(service_id=service_id).select_related('consumable')
        return Response(ServiceConsumableSerializer(qs, many=True).data)

    def post(self, request, service_id):
        service = self._check_service(request, service_id)
        if not service:
            return Response({'error': 'not_found'}, status=404)
        s = ServiceConsumableSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            s.save(service=service)
        except Exception:
            return Response({'error': 'This consumable is already linked to this service.'}, status=409)
        return Response(s.data, status=201)


class ServiceConsumableDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def delete(self, request, service_id, sc_id):
        try:
            link = ServiceConsumable.objects.get(id=sc_id, service_id=service_id, service__store=_store(request))
        except ServiceConsumable.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        link.delete()
        return Response(status=204)


class ServiceDeductConsumablesView(APIView):
    """POST /services/<service_id>/deduct/?sessions=N — deduct consumable stock for N sessions."""
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, service_id):
        from apps.stores.models import ServiceCatalogue
        try:
            ServiceCatalogue.objects.get(id=service_id, store=_store(request))
        except ServiceCatalogue.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)

        sessions = int(request.query_params.get('sessions', 1))
        if sessions < 1:
            return Response({'error': 'sessions must be >= 1'}, status=400)

        links = ServiceConsumable.objects.filter(service_id=service_id).select_related('consumable')
        deducted = []
        for link in links:
            qty = link.quantity_per_session * sessions
            c = link.consumable
            c.current_stock = max(0, c.current_stock - qty)
            c.save(update_fields=['current_stock'])
            deducted.append({'consumable': c.name, 'deducted': str(qty), 'remaining': str(c.current_stock)})

        return Response({'sessions': sessions, 'deducted': deducted})


# ── Equipment (#149) ──────────────────────────────────────────────────────────

class EquipmentListView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        qs = Equipment.objects.filter(store=_store(request))
        if request.query_params.get('maintenance_due') == 'true':
            from datetime import date
            qs = qs.filter(next_maintenance_date__lte=date.today())
        if request.query_params.get('condition'):
            qs = qs.filter(condition=request.query_params['condition'])
        return Response(EquipmentSerializer(qs, many=True).data)

    def post(self, request):
        s = EquipmentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(store=_store(request))
        return Response(s.data, status=201)


class EquipmentDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def _get(self, request, equipment_id):
        try:
            return Equipment.objects.get(id=equipment_id, store=_store(request))
        except Equipment.DoesNotExist:
            return None

    def get(self, request, equipment_id):
        obj = self._get(request, equipment_id)
        if not obj:
            return Response({'error': 'not_found'}, status=404)
        return Response(EquipmentSerializer(obj).data)

    def patch(self, request, equipment_id):
        obj = self._get(request, equipment_id)
        if not obj:
            return Response({'error': 'not_found'}, status=404)
        s = EquipmentSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def delete(self, request, equipment_id):
        obj = self._get(request, equipment_id)
        if not obj:
            return Response({'error': 'not_found'}, status=404)
        obj.delete()
        return Response(status=204)


class MaintenanceRecordView(APIView):
    """POST a maintenance record for a piece of equipment. GET lists them."""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_equipment(self, request, equipment_id):
        try:
            return Equipment.objects.get(id=equipment_id, store=_store(request))
        except Equipment.DoesNotExist:
            return None

    def get(self, request, equipment_id):
        if not self._get_equipment(request, equipment_id):
            return Response({'error': 'not_found'}, status=404)
        qs = MaintenanceRecord.objects.filter(equipment_id=equipment_id)
        return Response(MaintenanceRecordSerializer(qs, many=True).data)

    def post(self, request, equipment_id):
        equipment = self._get_equipment(request, equipment_id)
        if not equipment:
            return Response({'error': 'not_found'}, status=404)
        s = MaintenanceRecordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(equipment=equipment)
        return Response(MaintenanceRecordSerializer(s.instance).data, status=201)


# ── Resources (#150) ──────────────────────────────────────────────────────────

class ResourceListView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        qs = Resource.objects.filter(store=_store(request))
        if request.query_params.get('active_only') == 'true':
            qs = qs.filter(is_active=True)
        if request.query_params.get('type'):
            qs = qs.filter(resource_type=request.query_params['type'])
        return Response(ResourceSerializer(qs, many=True).data)

    def post(self, request):
        s = ResourceSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(store=_store(request))
        return Response(s.data, status=201)


class ResourceDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def _get(self, request, resource_id):
        try:
            return Resource.objects.get(id=resource_id, store=_store(request))
        except Resource.DoesNotExist:
            return None

    def get(self, request, resource_id):
        obj = self._get(request, resource_id)
        if not obj:
            return Response({'error': 'not_found'}, status=404)
        return Response(ResourceSerializer(obj).data)

    def patch(self, request, resource_id):
        obj = self._get(request, resource_id)
        if not obj:
            return Response({'error': 'not_found'}, status=404)
        s = ResourceSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def delete(self, request, resource_id):
        obj = self._get(request, resource_id)
        if not obj:
            return Response({'error': 'not_found'}, status=404)
        obj.delete()
        return Response(status=204)


class ResourceAllocationListView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        qs = ResourceAllocation.objects.filter(resource__store=_store(request)).select_related('resource')
        if request.query_params.get('date'):
            qs = qs.filter(date=request.query_params['date'])
        if request.query_params.get('resource_id'):
            qs = qs.filter(resource_id=request.query_params['resource_id'])
        return Response(ResourceAllocationSerializer(qs, many=True).data)

    def post(self, request):
        s = ResourceAllocationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        resource = s.validated_data['resource']
        if resource.store != _store(request):
            return Response({'error': 'resource not found'}, status=404)
        s.save()
        return Response(s.data, status=201)


class ResourceAllocationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def delete(self, request, allocation_id):
        try:
            obj = ResourceAllocation.objects.get(id=allocation_id, resource__store=_store(request))
        except ResourceAllocation.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        obj.delete()
        return Response(status=204)
