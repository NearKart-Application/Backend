"""
NearKart — Auth Serializers
"""
import re
from rest_framework import serializers
from .models import User


class OTPSendSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    is_signup    = serializers.BooleanField(default=False, required=False)

    def validate_phone_number(self, value):
        cleaned = re.sub(r'\s+', '', value)
        if not re.match(r'^\+91[6-9]\d{9}$', cleaned):
            raise serializers.ValidationError(
                'Enter a valid Indian mobile number in +91XXXXXXXXXX format.'
            )
        return cleaned


class OTPVerifySerializer(serializers.Serializer):
    phone_number  = serializers.CharField(max_length=15)
    otp           = serializers.CharField(min_length=6, max_length=6)
    referral_code = serializers.CharField(max_length=16, required=False, allow_blank=True, default='')

    def validate_phone_number(self, value):
        return re.sub(r'\s+', '', value)

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
