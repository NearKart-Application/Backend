"""
NearKart — Notifications Serializers
"""
from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ['id', 'notification_type', 'title', 'body', 'data', 'is_read', 'created_at']
        read_only_fields = fields


class DeviceTokenRegisterSerializer(serializers.Serializer):
    fcm_token   = serializers.CharField(max_length=512)
    device_type = serializers.ChoiceField(choices=[('android', 'Android'), ('ios', 'iOS')])
