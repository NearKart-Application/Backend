"""
NearKart — Admin Panel Admin
Shopify-grade admin for PromoBanner, AdminActivityLog, Category,
OfferTemplate, AdminProfile.
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from apps.locations.models import LocationMaster as _LocationMaster
from .forms import AdminProfileForm
from .models import PromoBanner, AdminActivityLog, Category, OfferTemplate, AdminProfile


# ─── Helper ───────────────────────────────────────────────────────────────────

def _badge(text, bg, color):
    return format_html(
        '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:{};color:{}">{}</span>',
        bg, color, text
    )


# ─── Promo Banner ─────────────────────────────────────────────────────────────

@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display    = [
        'title', 'badge_text', 'target_city', 'link_type',
        'display_order', 'is_active_badge', 'schedule_status', 'is_paid',
    ]
    list_filter     = ['is_active', 'is_paid', 'link_type']
    search_fields   = ['title', 'subtitle', 'target_city']
    list_editable   = ['display_order']
    ordering        = ['display_order', '-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    raw_id_fields   = ['created_by']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Banner Content', {'fields': ('title', 'subtitle', 'badge_text', 'image_url')}),
        ('Link Action',    {'fields': ('link_type', 'link_value')}),
        ('Targeting',      {'fields': ('target_city', 'display_order', 'is_active', 'is_paid')}),
        ('Schedule',       {'fields': ('starts_at', 'ends_at')}),
        ('Meta',           {'fields': ('created_by', 'created_at', 'updated_at')}),
    )

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#e2e3e5', '#383d41')

    @admin.display(description='Schedule')
    def schedule_status(self, obj):
        now = timezone.now()
        if obj.starts_at and now < obj.starts_at:
            return _badge('Scheduled', '#cce5ff', '#004085')
        if obj.ends_at and now > obj.ends_at:
            return _badge('Ended', '#f8d7da', '#721c24')
        if obj.starts_at or obj.ends_at:
            return _badge('Live', '#d4edda', '#155724')
        return format_html('<span style="color:#999">Always On</span>')


# ─── Category ─────────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display    = ['name', 'icon', 'slug', 'store_count', 'display_order',
                       'is_active_badge', 'created_at']
    list_filter     = ['is_active']
    search_fields   = ['name', 'slug']
    list_editable   = ['display_order']
    ordering        = ['display_order', 'name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    list_per_page   = 25
    raw_id_fields   = ['created_by']

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#e2e3e5', '#383d41')

    @admin.display(description='Stores')
    def store_count(self, obj):
        """
        Count stores whose category value matches this Category slug.
        Works when admin_panel.Category.slug matches stores.StoreCategory values.
        """
        from apps.stores.models import Store
        return Store.objects.filter(category=obj.slug, is_active=True).count()


# ─── Offer Template ───────────────────────────────────────────────────────────

@admin.register(OfferTemplate)
class OfferTemplateAdmin(admin.ModelAdmin):
    list_display    = [
        'name', 'emoji', 'badge_text', 'default_discount_pct',
        'is_active_badge', 'is_default', 'display_order',
    ]
    list_filter     = ['is_active', 'is_default']
    search_fields   = ['name', 'badge_text']
    list_editable   = ['display_order']
    ordering        = ['display_order', 'name']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page   = 25
    raw_id_fields   = ['created_by']

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#e2e3e5', '#383d41')


# ─── Admin Activity Log (read-only audit trail) ───────────────────────────────

@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    list_display    = [
        'admin', 'action_badge', 'target_type', 'target_label', 'detail', 'created_at',
    ]
    list_filter     = ['action', 'target_type']
    search_fields   = ['admin__phone_number', 'action', 'target_label', 'detail']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['admin']
    readonly_fields = [
        'admin', 'action', 'target_type', 'target_id',
        'target_label', 'detail', 'created_at', 'updated_at',
    ]

    @admin.display(description='Action', ordering='action')
    def action_badge(self, obj):
        action_lower = (obj.action or '').lower()
        if any(k in action_lower for k in ('suspend', 'delete', 'reject', 'ban', 'blacklist')):
            return _badge(obj.action, '#f8d7da', '#721c24')
        elif any(k in action_lower for k in ('verify', 'approve', 'activate', 'unsuspend')):
            return _badge(obj.action, '#d4edda', '#155724')
        return _badge(obj.action, '#e2e3e5', '#383d41')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ─── Admin Profile ─────────────────────────────────────────────────────────────

@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display    = [
        'user_phone', 'admin_level_badge',
        'assigned_state', 'assigned_district', 'assigned_city', 'assigned_area',
        'is_active_badge',
    ]
    list_filter     = ['admin_level', 'is_active']
    search_fields   = ['user__phone_number', 'assigned_state', 'assigned_district', 'assigned_city']
    ordering        = ['admin_level']
    list_per_page   = 25
    form            = AdminProfileForm
    list_select_related = ['user']
    raw_id_fields   = ['user']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Admin User',   {'fields': ('user', 'is_active')}),
        ('Access Level', {'fields': ('admin_level',)}),
        ('Geographic Scope', {
            'description': 'Select the area this admin can manage. Master Admin: leave all blank. '
                           'State Admin: fill State only. District Admin: fill State + District. '
                           'City Admin: fill State + District + City. Area Admin: fill all four.',
            'fields': ('assigned_state', 'assigned_district', 'assigned_city', 'assigned_area'),
        }),
        ('Meta', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    class Media:
        js = ('admin_panel/js/admin_profile_chain.js',)
        css = {'all': ('admin_panel/css/admin_profile_chain.css',)}

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('location-options/', self.admin_site.admin_view(self._location_options_view),
                 name='adminprofile_location_options'),
        ]
        return custom + urls

    def _location_options_view(self, request):
        """AJAX endpoint — returns location options for chained selects (sourced from LocationMaster)."""
        field    = request.GET.get('field', '')
        state    = request.GET.get('state', '')
        district = request.GET.get('district', '')
        city     = request.GET.get('city', '')

        qs = _LocationMaster.objects.all()

        if field == 'state':
            options = list(
                qs.exclude(state='').values_list('state', flat=True).distinct().order_by('state')
            )
        elif field == 'district' and state:
            options = list(
                qs.filter(state=state).exclude(district='')
                .values_list('district', flat=True).distinct().order_by('district')
            )
        elif field == 'city' and district:
            options = list(
                qs.filter(state=state, district=district).exclude(city='')
                .values_list('city', flat=True).distinct().order_by('city')
            )
        elif field == 'area' and city:
            # area is free-text in LocationMaster (no area column); return empty
            options = []
        else:
            options = []

        return JsonResponse({'options': options})

    def change_view(self, request, *args, **kwargs):
        # Inject the AJAX endpoint URL into the page so JS can find it
        extra = {'location_options_url': '/admin/admin_panel/adminprofile/location-options/'}
        kwargs.setdefault('extra_context', {}).update(extra)
        return super().change_view(request, *args, **kwargs)

    def add_view(self, request, *args, **kwargs):
        extra = {'location_options_url': '/admin/admin_panel/adminprofile/location-options/'}
        kwargs.setdefault('extra_context', {}).update(extra)
        return super().add_view(request, *args, **kwargs)

    @admin.display(description='Phone', ordering='user__phone_number')
    def user_phone(self, obj):
        return obj.user.phone_number

    @admin.display(description='Level', ordering='admin_level')
    def admin_level_badge(self, obj):
        colors = {
            'master':   ('#721c24', '#ffffff'),
            'state':    ('#004085', '#ffffff'),
            'district': ('#155724', '#ffffff'),
            'city':     ('#856404', '#ffffff'),
            'area':     ('#383d41', '#ffffff'),
        }
        bg, color = colors.get(obj.admin_level, ('#383d41', '#ffffff'))
        return _badge(obj.get_admin_level_display(), bg, color)

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#e2e3e5', '#383d41')
