from django.urls import path
from .views import (
    ReservationCreateView,
    ReservationListView,
    ReservationDetailView,
    ReservationStatusView,
    ReservationCancelView,
    ReservationCartView,
    ReservationReceiptView,
    ReservationWaitlistView,
    ReservationReturnView,
)

urlpatterns = [
    path('',                                     ReservationCreateView.as_view(),  name='reservation-create'),
    path('list/',                                ReservationListView.as_view(),    name='reservation-list'),
    path('cart/',                                ReservationCartView.as_view(),    name='reservation-cart'),
    path('waitlist/',                            ReservationWaitlistView.as_view(), name='reservation-waitlist'),
    path('<uuid:reservation_id>/',               ReservationDetailView.as_view(),  name='reservation-detail'),
    path('<uuid:reservation_id>/status/',        ReservationStatusView.as_view(),  name='reservation-status'),
    path('<uuid:reservation_id>/cancel/',        ReservationCancelView.as_view(),  name='reservation-cancel'),
    path('<uuid:reservation_id>/receipt/',       ReservationReceiptView.as_view(), name='reservation-receipt'),
    path('<uuid:reservation_id>/return/',        ReservationReturnView.as_view(),  name='reservation-return'),
]
