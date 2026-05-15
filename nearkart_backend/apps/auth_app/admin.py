from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPToken, DeviceToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['phone_number', 'role', 'full_name', 'is_active', 'created_at']
    list_filter = ['role', 'is_active']
    search_fields = ['phone_number', 'full_name']
    ordering = ['-created_at']
    fieldsets = (
        (None, {'fields': ('phone_number', 'role', 'full_name', 'email')}),
        ('Location', {'fields': ('registered_location',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'fields': ('phone_number', 'role')}),
    )


@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'expires_at', 'is_used', 'attempts', 'created_at']
    list_filter = ['is_used']
    search_fields = ['user__phone_number']
    readonly_fields = ['otp_hash']


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'is_active', 'created_at']
    list_filter = ['device_type', 'is_active']
    search_fields = ['user__phone_number']
