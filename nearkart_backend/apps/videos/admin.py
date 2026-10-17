"""
NearKart — Videos Admin
Shopify-grade admin for Video, VideoLike, VideoSave, VideoProductTag.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Video, VideoLike, VideoSave, VideoProductTag


# ─── Helper ───────────────────────────────────────────────────────────────────

def _badge(text, bg, color):
    return format_html(
        '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:{};color:{}">{}</span>',
        bg, color, text
    )


# ─── Bulk actions ─────────────────────────────────────────────────────────────

@admin.action(description='Make selected videos visible')
def make_visible(modeladmin, request, queryset):
    updated = queryset.update(is_visible=True)
    modeladmin.message_user(request, f'{updated} video(s) made visible.')


@admin.action(description='Hide selected videos')
def make_invisible(modeladmin, request, queryset):
    updated = queryset.update(is_visible=False)
    modeladmin.message_user(request, f'{updated} video(s) hidden.')


# ─── Video Admin ──────────────────────────────────────────────────────────────

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display    = [
        'title', 'store', 'status_badge', 'video_type',
        'duration_seconds', 'view_count', 'like_count',
        'engagement_rate', 'visible_badge', 'created_at',
    ]
    list_filter     = ['status', 'is_visible', 'video_type']
    search_fields   = ['title', 'store__name', 'store__owner__phone_number']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    show_full_result_count = False
    list_select_related    = ['store']
    raw_id_fields   = ['store', 'product']
    readonly_fields = ['id', 'raw_s3_key', 'hls_s3_key', 'view_count',
                       'like_count', 'created_at', 'updated_at']
    actions         = [make_visible, make_invisible]

    fieldsets = (
        ('Video Info',  {'fields': ('store', 'title', 'description', 'video_type', 'product')}),
        ('Media',       {'fields': ('raw_s3_key', 'hls_s3_key', 'thumbnail_url', 'video_url')}),
        ('Status',      {'fields': ('status', 'is_visible', 'expires_at', 'duration_seconds')}),
        ('Stats',       {'fields': ('view_count', 'like_count')}),
        ('Location',    {'fields': ('location', 'locality'), 'classes': ('collapse',)}),
        ('Meta',        {'fields': ('id', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'pending_upload': ('#fff3cd', '#856404'),
            'processing':     ('#cce5ff', '#004085'),
            'ready':          ('#d4edda', '#155724'),
            'failed':         ('#f8d7da', '#721c24'),
            'expired':        ('#e2e3e5', '#383d41'),
        }
        bg, color = colors.get(obj.status, ('#e2e3e5', '#333'))
        return _badge(obj.get_status_display(), bg, color)

    @admin.display(description='Visible', ordering='is_visible')
    def visible_badge(self, obj):
        if obj.is_visible:
            return _badge('Yes', '#d4edda', '#155724')
        return _badge('Hidden', '#e2e3e5', '#383d41')

    @admin.display(description='Engagement %')
    def engagement_rate(self, obj):
        if not obj.view_count:
            return format_html('<span style="color:#999">—</span>')
        rate = obj.like_count / obj.view_count * 100
        color = '#155724' if rate >= 5 else ('#856404' if rate >= 2 else '#721c24')
        return format_html(
            '<span style="color:{};font-weight:600">{:.1f}%</span>', color, rate
        )


# ─── VideoLike Admin ──────────────────────────────────────────────────────────

@admin.register(VideoLike)
class VideoLikeAdmin(admin.ModelAdmin):
    list_display    = ['user', 'video', 'created_at']
    search_fields   = ['user__phone_number', 'video__title']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['user', 'video']
    readonly_fields = ['created_at']


# ─── VideoSave Admin ──────────────────────────────────────────────────────────

@admin.register(VideoSave)
class VideoSaveAdmin(admin.ModelAdmin):
    list_display    = ['user', 'video', 'created_at']
    search_fields   = ['user__phone_number', 'video__title']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['user', 'video']
    readonly_fields = ['created_at']


# ─── VideoProductTag Admin ────────────────────────────────────────────────────

@admin.register(VideoProductTag)
class VideoProductTagAdmin(admin.ModelAdmin):
    list_display    = ['video', 'product', 'x_pct', 'y_pct', 'created_at']
    search_fields   = ['video__title', 'product__name']
    list_per_page   = 25
    list_select_related    = ['video', 'product']
    raw_id_fields   = ['video', 'product']
    readonly_fields = ['id', 'created_at']
