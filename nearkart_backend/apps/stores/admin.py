"""
NearKart — Stores Admin
Shopify-grade admin for Store, StoreHours, StoreFollow, StoreReview, StoreOffer,
Invoice, StaffMember, ServiceCatalogue, DiscountCode, WebsiteRequest,
BroadcastChannel, BroadcastPost, CustomerBlockedStore.
"""
from django.contrib import admin
from django.utils.html import format_html

from core.admin_scope import get_store_scope
from .models import (
    Store, StoreHours, StoreFollow, StoreReview, StoreOffer, Invoice,
    StaffMember, ServiceCatalogue, DiscountCode, WebsiteRequest,
    BroadcastChannel, BroadcastPost, CustomerBlockedStore,
)


# ─── Chained location filters ────────────────────────────────────────────────
# Each level narrows based on what the parent level has selected.
# e.g. selecting "Andhra Pradesh" as State → District only shows AP districts.
# This makes filters usable even with millions of rows.

class StateFilter(admin.SimpleListFilter):
    title = 'State'
    parameter_name = 'state'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        vals = qs.exclude(state='').values_list('state', flat=True).distinct().order_by('state')
        return [(v, v) for v in vals if v]

    def queryset(self, request, queryset):
        return queryset.filter(state=self.value()) if self.value() else queryset


class DistrictFilter(admin.SimpleListFilter):
    title = 'District'
    parameter_name = 'district'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        # Chain: only show districts inside the selected state
        if request.GET.get('state'):
            qs = qs.filter(state=request.GET['state'])
        vals = qs.exclude(district='').values_list('district', flat=True).distinct().order_by('district')
        return [(v, v) for v in vals if v]

    def queryset(self, request, queryset):
        return queryset.filter(district=self.value()) if self.value() else queryset


class CityFilter(admin.SimpleListFilter):
    title = 'City'
    parameter_name = 'city'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        if request.GET.get('district'):
            qs = qs.filter(district=request.GET['district'])
        elif request.GET.get('state'):
            qs = qs.filter(state=request.GET['state'])
        vals = qs.exclude(city='').values_list('city', flat=True).distinct().order_by('city')
        return [(v, v) for v in vals if v]

    def queryset(self, request, queryset):
        return queryset.filter(city=self.value()) if self.value() else queryset


class AreaFilter(admin.SimpleListFilter):
    title = 'Area / Village'
    parameter_name = 'area'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        if request.GET.get('city'):
            qs = qs.filter(city=request.GET['city'])
        elif request.GET.get('district'):
            qs = qs.filter(district=request.GET['district'])
        elif request.GET.get('state'):
            qs = qs.filter(state=request.GET['state'])
        vals = qs.exclude(area='').values_list('area', flat=True).distinct().order_by('area')
        return [(v, v) for v in vals if v]

    def queryset(self, request, queryset):
        return queryset.filter(area=self.value()) if self.value() else queryset


class CountryFilter(admin.SimpleListFilter):
    title = 'Country'
    parameter_name = 'country'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        vals = qs.exclude(country='').values_list('country', flat=True).distinct().order_by('country')
        return [(v, v) for v in vals if v]

    def queryset(self, request, queryset):
        return queryset.filter(country=self.value()) if self.value() else queryset


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _badge(text, bg, color):
    return format_html(
        '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:{};color:{}">{}</span>',
        bg, color, text
    )


# ─── Inlines ──────────────────────────────────────────────────────────────────

class StoreHoursInline(admin.TabularInline):
    model   = StoreHours
    extra   = 0
    fields  = ['day', 'open_time', 'close_time', 'is_closed']
    ordering = ['day']


class ServiceCatalogueInline(admin.TabularInline):
    model   = ServiceCatalogue
    extra   = 0
    fields  = ['name', 'price_from', 'price_to', 'duration_minutes', 'is_active', 'sort_order']
    ordering = ['sort_order', 'name']
    show_change_link = True


# ─── Bulk actions ─────────────────────────────────────────────────────────────

@admin.action(description='Verify selected stores')
def verify_stores(modeladmin, request, queryset):
    updated = queryset.update(is_verified=True)
    modeladmin.message_user(request, f'{updated} store(s) marked as verified.')


@admin.action(description='Unverify selected stores')
def unverify_stores(modeladmin, request, queryset):
    updated = queryset.update(is_verified=False)
    modeladmin.message_user(request, f'{updated} store(s) unverified.')


@admin.action(description='Activate selected stores')
def activate_stores(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} store(s) activated.')


@admin.action(description='Deactivate selected stores')
def deactivate_stores(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} store(s) deactivated.')


# ─── Store Admin ──────────────────────────────────────────────────────────────

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display   = [
        'name', 'owner_phone', 'category', 'city', 'state',
        'rating_display', 'verified_badge', 'active_badge', 'open_badge',
        'created_at',
    ]
    list_filter    = [
        'category', 'is_verified', 'is_active', 'is_open', 'vendor_type',
        'is_women_owned', 'is_home_based',
        CountryFilter, StateFilter, DistrictFilter, CityFilter, AreaFilter,
    ]
    search_fields  = ['name', 'owner__phone_number', 'city', 'state', 'locality', 'district']
    ordering       = ['-created_at']
    date_hierarchy = 'created_at'
    list_per_page  = 25
    show_full_result_count = False
    list_select_related    = ['owner']
    raw_id_fields  = ['owner']
    readonly_fields = ['qr_code_url', 'performance_score', 'created_at', 'updated_at']
    actions        = [verify_stores, unverify_stores, activate_stores, deactivate_stores]
    inlines        = [StoreHoursInline, ServiceCatalogueInline]

    fieldsets = (
        ('Store Info',  {'fields': ('owner', 'name', 'description', 'category',
                                    'store_type', 'vendor_type', 'phone')}),
        ('Location',    {'fields': ('address', 'area', 'locality', 'city',
                                    'district', 'state', 'country', 'location')}),
        ('Status',      {'fields': ('is_active', 'is_verified', 'is_open', 'is_women_owned',
                                    'is_home_based', 'privacy_mode', 'holiday_mode')}),
        ('Media',       {'fields': ('logo_url', 'banner_url', 'qr_code_url', 'license_url', 'gst_url')}),
        ('Performance', {'fields': ('performance_score', 'wallet_balance', 'created_at', 'updated_at')}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        scope = get_store_scope(request)
        return qs.filter(**scope) if scope else qs

    @admin.display(description='Owner Phone', ordering='owner__phone_number')
    def owner_phone(self, obj):
        return obj.owner.phone_number

    @admin.display(description='Score', ordering='performance_score')
    def rating_display(self, obj):
        score = obj.performance_score
        if score >= 4.0:
            bg, color = '#d4edda', '#155724'
        elif score >= 2.5:
            bg, color = '#fff3cd', '#856404'
        else:
            bg, color = '#f8d7da', '#721c24'
        return _badge(f'{score:.1f}', bg, color)

    @admin.display(description='Verified', ordering='is_verified')
    def verified_badge(self, obj):
        if obj.is_verified:
            return _badge('Verified', '#d4edda', '#155724')
        return _badge('Unverified', '#f8d7da', '#721c24')

    @admin.display(description='Active', ordering='is_active')
    def active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#f8d7da', '#721c24')

    @admin.display(description='Open', ordering='is_open')
    def open_badge(self, obj):
        if obj.is_open:
            return _badge('Open', '#cce5ff', '#004085')
        return _badge('Closed', '#e2e3e5', '#383d41')


# ─── Store Review Admin ───────────────────────────────────────────────────────

@admin.register(StoreReview)
class StoreReviewAdmin(admin.ModelAdmin):
    list_display    = ['store', 'user_phone', 'rating_stars', 'is_verified', 'created_at']
    list_filter     = ['rating', 'is_verified']
    search_fields   = ['store__name', 'user__phone_number', 'comment']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['store', 'user']
    raw_id_fields   = ['store', 'user']
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='User', ordering='user__phone_number')
    def user_phone(self, obj):
        return obj.user.phone_number

    @admin.display(description='Rating', ordering='rating')
    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        colors = {5: '#155724', 4: '#155724', 3: '#856404', 2: '#721c24', 1: '#721c24'}
        return format_html(
            '<span style="color:{};font-size:13px">{}</span>',
            colors.get(obj.rating, '#333'), stars
        )


# ─── Store Follow Admin ───────────────────────────────────────────────────────

@admin.register(StoreFollow)
class StoreFollowAdmin(admin.ModelAdmin):
    list_display    = ['user', 'store', 'created_at']
    search_fields   = ['store__name', 'user__phone_number']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    list_select_related    = ['user', 'store']
    show_full_result_count = False


# ─── Store Offer Admin ────────────────────────────────────────────────────────

@admin.register(StoreOffer)
class StoreOfferAdmin(admin.ModelAdmin):
    list_display    = ['store', 'title', 'discount_pct', 'valid_till', 'active_badge', 'created_at']
    list_filter     = ['is_active']
    search_fields   = ['store__name', 'title']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['store']
    raw_id_fields   = ['store']
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='Active', ordering='is_active')
    def active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#e2e3e5', '#383d41')


# ─── Invoice Admin ────────────────────────────────────────────────────────────

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display    = ['id', 'store', 'customer_name', 'customer_phone', 'total', 'is_sent', 'created_at']
    list_filter     = ['is_sent']
    search_fields   = ['store__name', 'customer_name', 'customer_phone', 'customer_ns_code']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    show_full_result_count = False
    list_select_related    = ['store']
    raw_id_fields   = ['store']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Invoice',   {'fields': ('store', 'customer_name', 'customer_phone', 'customer_ns_code')}),
        ('Financial', {'fields': ('total', 'discount_type', 'discount_value', 'gstin', 'gst_rate')}),
        ('Items',     {'fields': ('items', 'notes')}),
        ('Status',    {'fields': ('is_sent', 'id', 'created_at', 'updated_at')}),
    )


# ─── Discount Code Admin ──────────────────────────────────────────────────────

@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display    = ['code', 'store', 'discount_type', 'value', 'uses_count',
                       'max_uses', 'valid_till', 'active_badge', 'created_at']
    list_filter     = ['is_active', 'discount_type']
    search_fields   = ['code', 'store__name']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['store']
    raw_id_fields   = ['store', 'created_by']
    readonly_fields = ['uses_count', 'created_at', 'updated_at']

    @admin.display(description='Active', ordering='is_active')
    def active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#e2e3e5', '#383d41')


# ─── Website Request Admin ────────────────────────────────────────────────────

@admin.register(WebsiteRequest)
class WebsiteRequestAdmin(admin.ModelAdmin):
    list_display    = ['store', 'status_badge', 'domain_preference', 'reviewed_at', 'created_at']
    list_filter     = ['status']
    search_fields   = ['store__name', 'domain_preference']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['store']
    raw_id_fields   = ['store']
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at']

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'pending':  ('#fff3cd', '#856404'),
            'approved': ('#d4edda', '#155724'),
            'rejected': ('#f8d7da', '#721c24'),
        }
        bg, color = colors.get(obj.status, ('#e2e3e5', '#333'))
        return _badge(obj.get_status_display(), bg, color)


# ─── Staff Member Admin ───────────────────────────────────────────────────────

@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display    = ['user', 'store', 'role', 'is_active', 'invited_by', 'created_at']
    list_filter     = ['role', 'is_active']
    search_fields   = ['user__phone_number', 'user__full_name', 'store__name']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['user', 'store', 'invited_by']
    raw_id_fields   = ['store', 'user', 'invited_by']
    readonly_fields = ['created_at', 'updated_at']


# ─── Broadcast Channel Admin ──────────────────────────────────────────────────

class BroadcastPostInline(admin.TabularInline):
    model   = BroadcastPost
    extra   = 0
    fields  = ['content', 'image_url', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True


@admin.register(BroadcastChannel)
class BroadcastChannelAdmin(admin.ModelAdmin):
    list_display    = ['name', 'store', 'auto_subscribe', 'created_at']
    search_fields   = ['name', 'store__name']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['store']
    raw_id_fields   = ['store']
    readonly_fields = ['created_at', 'updated_at']
    inlines         = [BroadcastPostInline]


# ─── Customer Blocked Store Admin ─────────────────────────────────────────────

@admin.register(CustomerBlockedStore)
class CustomerBlockedStoreAdmin(admin.ModelAdmin):
    list_display    = ['customer', 'store', 'created_at']
    search_fields   = ['customer__phone_number', 'store__name']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    show_full_result_count = False
    list_select_related    = ['customer', 'store']
    raw_id_fields   = ['customer', 'store']
    readonly_fields = ['created_at', 'updated_at']
