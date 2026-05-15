from django.contrib import admin
from .models import Store, StoreHours, StoreFollow, StoreReview


class StoreHoursInline(admin.TabularInline):
    model  = StoreHours
    extra  = 0
    fields = ['day', 'open_time', 'close_time', 'is_closed']


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display   = ['name', 'owner', 'category', 'locality', 'is_verified', 'is_active', 'is_open', 'performance_score']
    list_filter    = ['category', 'is_verified', 'is_active', 'is_open']
    search_fields  = ['name', 'owner__phone_number', 'locality']
    readonly_fields = ['qr_code_url', 'performance_score', 'created_at', 'updated_at']
    inlines        = [StoreHoursInline]
    actions        = ['verify_stores', 'unverify_stores']

    def verify_stores(self, request, queryset):
        queryset.update(is_verified=True)
    verify_stores.short_description = 'Mark selected stores as verified'

    def unverify_stores(self, request, queryset):
        queryset.update(is_verified=False)
    unverify_stores.short_description = 'Mark selected stores as unverified'


@admin.register(StoreReview)
class StoreReviewAdmin(admin.ModelAdmin):
    list_display  = ['store', 'user', 'rating', 'created_at']
    list_filter   = ['rating']
    search_fields = ['store__name', 'user__phone_number']


@admin.register(StoreFollow)
class StoreFollowAdmin(admin.ModelAdmin):
    list_display  = ['user', 'store', 'created_at']
    search_fields = ['store__name', 'user__phone_number']
