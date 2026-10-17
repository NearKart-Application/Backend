"""
NearKart — Auth Serializers
"""
import re
from rest_framework import serializers
from .models import User


class OTPSendSerializer(serializers.Serializer):
    phone_number     = serializers.CharField(max_length=15)
    is_signup        = serializers.BooleanField(default=False, required=False)
    delivery_method  = serializers.ChoiceField(choices=['sms', 'voice'], default='sms', required=False)

    def validate_phone_number(self, value):
        cleaned = re.sub(r'\s+', '', value)
        if not re.match(r'^\+\d{7,15}$', cleaned):
            raise serializers.ValidationError(
                'Enter a valid phone number with country code (e.g. +919876543210).'
            )
        return cleaned


class OTPVerifySerializer(serializers.Serializer):
    phone_number  = serializers.CharField(max_length=15)
    otp           = serializers.CharField(min_length=6, max_length=6)
    referral_code = serializers.CharField(max_length=16, required=False, allow_blank=True, default='')

    def validate_phone_number(self, value):
        value = re.sub(r'\s+', '', value)
        if not re.match(r'^\+\d{7,15}$', value):
            raise serializers.ValidationError('Enter a valid phone number with country code (e.g. +919876543210).')
        return value

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('OTP must be 6 digits.')
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'profile_id', 'phone_number', 'role', 'full_name', 'email', 'avatar', 'admin_assigned_city', 'is_suspended', 'created_at']
        # role is excluded from read_only_fields — it can be set via PATCH when empty (new user).
        # MeView.patch() enforces the "only settable once" constraint.
        read_only_fields = ['id', 'profile_id', 'phone_number', 'is_suspended', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated or getattr(user, 'role', '') not in ('admin', 'master_admin'):
            data.pop('admin_assigned_city', None)
            data.pop('is_suspended', None)
        return data


class UserSearchSerializer(serializers.ModelSerializer):
    """Public search result — exposes name, profile_id, and role only. No phone number."""
    class Meta:
        model = User
        fields = ['id', 'profile_id', 'full_name', 'role']
        read_only_fields = fields


class LocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
