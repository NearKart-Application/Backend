from django.urls import path
from .views import (
    ConsumableListView, ConsumableDetailView,
    ServiceConsumableListView, ServiceConsumableDeleteView, ServiceDeductConsumablesView,
    EquipmentListView, EquipmentDetailView, MaintenanceRecordView,
    ResourceListView, ResourceDetailView,
    ResourceAllocationListView, ResourceAllocationDetailView,
)

urlpatterns = [
    # Consumables
    path('consumables/',                                    ConsumableListView.as_view(),   name='svc-consumables'),
    path('consumables/<uuid:consumable_id>/',               ConsumableDetailView.as_view(), name='svc-consumable-detail'),
    # Service ↔ Consumable
    path('services/<uuid:service_id>/consumables/',         ServiceConsumableListView.as_view(),  name='svc-service-consumables'),
    path('services/<uuid:service_id>/consumables/<uuid:sc_id>/', ServiceConsumableDeleteView.as_view(), name='svc-service-consumable-delete'),
    path('services/<uuid:service_id>/deduct/',              ServiceDeductConsumablesView.as_view(), name='svc-deduct'),
    # Equipment
    path('equipment/',                                      EquipmentListView.as_view(),   name='svc-equipment'),
    path('equipment/<uuid:equipment_id>/',                  EquipmentDetailView.as_view(), name='svc-equipment-detail'),
    path('equipment/<uuid:equipment_id>/maintenance/',      MaintenanceRecordView.as_view(), name='svc-maintenance'),
    # Resources
    path('resources/',                                      ResourceListView.as_view(),   name='svc-resources'),
    path('resources/<uuid:resource_id>/',                   ResourceDetailView.as_view(), name='svc-resource-detail'),
    path('allocations/',                                    ResourceAllocationListView.as_view(),  name='svc-allocations'),
    path('allocations/<uuid:allocation_id>/',               ResourceAllocationDetailView.as_view(), name='svc-allocation-detail'),
]
