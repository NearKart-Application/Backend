from django.contrib import admin

from .models import Video, VideoLike


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display    = ['title', 'store', 'status', 'duration_seconds',
                       'view_count', 'like_count', 'is_visible', 'expires_at', 'created_at']
    list_filter     = ['status', 'is_visible']
    list_editable   = ['is_visible']
    search_fields   = ['title', 'store__name']
    readonly_fields = ['id', 'raw_s3_key', 'hls_s3_key', 'view_count',
                       'like_count', 'created_at', 'updated_at']
    ordering        = ['-created_at']


@admin.register(VideoLike)
class VideoLikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'created_at']
    readonly_fields = ['created_at']
