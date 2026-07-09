from django.urls import path
from .views import (
    NotificationListView,
    NotificationUnreadCountView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
    NotificationDeleteView,
    DeviceTokenRegisterView,
)

urlpatterns = [
    path('',                                    NotificationListView.as_view(),        name='notification-list'),
    path('unread-count/',                       NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('<uuid:notification_id>/read/',        NotificationMarkReadView.as_view(),    name='notification-mark-read'),
    path('<uuid:notification_id>/',             NotificationDeleteView.as_view(),      name='notification-delete'),
    path('read-all/',                           NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('device-token/',                       DeviceTokenRegisterView.as_view(),     name='device-token-register'),
]
