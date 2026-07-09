"""
NearKart — Notifications Views
"""
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from apps.auth_app.models import DeviceToken
from .models import Notification
from .serializers import NotificationSerializer, DeviceTokenRegisterSerializer

logger = logging.getLogger(__name__)
_TAG = 'Notifications'


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='List my notifications',
        description='Returns all notifications for the authenticated user, newest first.',
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request):
        page      = max(int(request.query_params.get('page', 1)), 1)
        page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 100)
        qs        = Notification.objects.filter(recipient=request.user).order_by('-created_at')
        total     = qs.count()
        offset    = (page - 1) * page_size
        results   = qs[offset: offset + page_size]
        return Response({
            'count':    total,
            'page':     page,
            'has_next': offset + page_size < total,
            'results':  NotificationSerializer(results, many=True).data,
        })


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Unread notification count',
        description='Returns the count of unread notifications for the badge.',
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread_count': count})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Mark notification as read',
        description='Marks a single notification as read.',
        request=None,
        responses={200: NotificationSerializer},
    )
    def post(self, request, notification_id):
        try:
            notif = Notification.objects.get(id=notification_id, recipient=request.user)
        except Notification.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Notification not found.'}, status=404)

        notif.is_read = True
        notif.save(update_fields=['is_read', 'updated_at'])
        return Response(NotificationSerializer(notif).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Mark all notifications as read',
        description='Marks all unread notifications as read.',
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'marked_read': count})


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Delete a notification',
        request=None,
        responses={204: None},
    )
    def delete(self, request, notification_id):
        try:
            notif = Notification.objects.get(id=notification_id, recipient=request.user)
        except Notification.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Notification not found.'}, status=404)
        notif.delete()
        return Response(status=204)


class DeviceTokenRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Register FCM device token',
        description='Register or update the FCM push notification token for this device. Call on every app launch.',
        request=DeviceTokenRegisterSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        ser = DeviceTokenRegisterSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        DeviceToken.objects.update_or_create(
            user=request.user,
            fcm_token=ser.validated_data['fcm_token'],
            defaults={
                'device_type': ser.validated_data['device_type'],
                'is_active': True,
            },
        )
        return Response({'message': 'Device token registered.'})
