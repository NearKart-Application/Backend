from django.urls import path
from .views import (
    ReservationCreateView,
    ReservationListView,
    ReservationDetailView,
    ReservationStatusView,
    ReservationCancelView,
)

urlpatterns = [
    path('',                              ReservationCreateView.as_view(), name='reservation-create'),
    path('list/',                         ReservationListView.as_view(),   name='reservation-list'),
    path('<uuid:reservation_id>/',        ReservationDetailView.as_view(), name='reservation-detail'),
    path('<uuid:reservation_id>/status/', ReservationStatusView.as_view(), name='reservation-status'),
    path('<uuid:reservation_id>/cancel/', ReservationCancelView.as_view(), name='reservation-cancel'),
]
