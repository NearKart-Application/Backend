"""
NearKart — Auth App Admin
Shopify-grade admin panel for User, OTPToken, DeviceToken.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count
from django.utils.html import format_html

from core.admin_scope import get_user_scope
from .models import User, OTPToken, DeviceToken, SocialAccount


# ─── Chained location filters ─────────────────────────────────────────────────

class UserStateFilter(admin.SimpleListFilter):
    title = 'State'
    parameter_name = 'location_state'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        vals = qs.exclude(location_state='').values_list('location_state', flat=True).distinct().order_by('location_state')
        return [(v, v) for v in vals if v]

    def queryset(self, request, queryset):
        return queryset.filter(location_state=self.value()) if self.value() else queryset


class UserDistrictFilter(admin.SimpleListFilter):
    title = 'District'
    parameter_name = 'location_district'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        # Chain: only show districts in the selected state
        if request.GET.get('location_state'):
            qs = qs.filter(location_state=request.GET['location_state'])
        vals = qs.exclude(location_district='').values_list('location_district', flat=True).distinct().order_by('location_district')
        return [(v, v) for v in vals if v]

    def queryset(self, request, queryset):
        return queryset.filter(location_district=self.value()) if self.value() else queryset


class UserCityFilter(admin.SimpleListFilter):
    title = 'City'
    parameter_name = 'location_city'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        if request.GET.get('location_district'):
            qs = qs.filter(location_district=request.GET['location_district'])
        elif request.GET.get('location_state'):
            qs = qs.filter(location_state=request.GET['location_state'])
        values = (
            qs.exclude(location_city__exact='')
            .values_list('location_city', flat=True)
            .distinct()
            .order_by('location_city')
        )
        return [(v, v) for v in values if v]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(location_city=self.value())
        return queryset


# ─── Bulk actions ─────────────────────────────────────────────────────────────

@admin.action(description='Suspend selected users')
def suspend_users(modeladmin, request, queryset):
    updated = queryset.filter(is_suspended=False).update(is_suspended=True, is_active=False)
    modeladmin.message_user(request, f'{updated} user(s) suspended.')


@admin.action(description='Activate selected users')
def activate_users(modeladmin, request, queryset):
    updated = queryset.filter(is_active=False).update(is_active=True)
    modeladmin.message_user(request, f'{updated} user(s) activated.')


@admin.action(description='Unsuspend selected users')
def unsuspend_users(modeladmin, request, queryset):
    updated = queryset.filter(is_suspended=True).update(is_suspended=False, is_active=True)
    modeladmin.message_user(request, f'{updated} user(s) unsuspended.')


# ─── User Admin ───────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display   = [
        'phone_number', 'full_name', 'role', 'store_count',
        'location_city', 'location_state',
        'active_badge', 'suspended_badge', 'created_at',
    ]
    list_filter    = ['role', 'is_active', 'is_suspended',
                      UserStateFilter, UserDistrictFilter, UserCityFilter]
    search_fields  = ['phone_number', 'full_name', 'email', 'profile_id']
    ordering       = ['-created_at']
    date_hierarchy = 'created_at'
    list_per_page  = 25
    show_full_result_count = False
    list_select_related    = True
    actions        = [suspend_users, activate_users, unsuspend_users]

    fieldsets = (
        ('Basic Info',  {'fields': ('phone_number', 'profile_id', 'role', 'full_name', 'email', 'avatar')}),
        ('Location',    {'fields': ('location_city', 'location_district', 'location_state',
                                    'admin_assigned_city', 'registered_location')}),
        ('Status',      {'fields': ('is_active', 'is_suspended', 'suspension_reason')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('phone_number', 'role')}),
    )
    readonly_fields = ['profile_id', 'created_at', 'updated_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request).annotate(_store_count=Count('stores', distinct=True))
        scope = get_user_scope(request)
        return qs.filter(**scope) if scope else qs

    @admin.display(description='Stores', ordering='_store_count')
    def store_count(self, obj):
        return obj._store_count

    @admin.display(description='Active', ordering='is_active')
    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
                'font-weight:600;background:#d4edda;color:#155724">Active</span>'
            )
        return format_html(
            '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
            'font-weight:600;background:#f8d7da;color:#721c24">Inactive</span>'
        )

    @admin.display(description='Suspended', ordering='is_suspended')
    def suspended_badge(self, obj):
        if obj.is_suspended:
            return format_html(
                '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
                'font-weight:600;background:#fff3cd;color:#856404">Suspended</span>'
            )
        return format_html(
            '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
            'font-weight:600;background:#d4edda;color:#155724">OK</span>'
        )


# ─── OTPToken Admin ───────────────────────────────────────────────────────────

@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    list_display    = ['user', 'expires_at', 'is_used', 'attempts', 'created_at']
    list_filter     = ['is_used']
    search_fields   = ['user__phone_number']
    readonly_fields = ['otp_hash', 'created_at', 'updated_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    list_select_related    = ['user']
    show_full_result_count = False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ─── SocialAccount Admin ──────────────────────────────────────────────────────

@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display    = ['user_phone', 'provider', 'provider_uid', 'created_at']
    list_filter     = ['provider']
    search_fields   = ['user__phone_number', 'provider_uid', 'extra_data']
    readonly_fields = ['created_at', 'updated_at', 'provider_uid', 'extra_data']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    list_select_related = ['user']
    raw_id_fields   = ['user']

    @admin.display(description='User', ordering='user__phone_number')
    def user_phone(self, obj):
        return obj.user.phone_number

    def has_add_permission(self, request):
        return False


# ─── DeviceToken Admin ────────────────────────────────────────────────────────

@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display    = ['user', 'device_type', 'is_active', 'created_at']
    list_filter     = ['device_type', 'is_active']
    search_fields   = ['user__phone_number']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    list_select_related    = ['user']
    show_full_result_count = False
