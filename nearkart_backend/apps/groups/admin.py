"""
NearKart — Groups Admin
Shopify-grade admin for Group, GroupMember, GroupSharedProduct, GroupMessage.
"""
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Group, GroupMember, GroupSharedProduct, GroupMessage


# ─── Helper ───────────────────────────────────────────────────────────────────

def _badge(text, bg, color):
    return format_html(
        '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:{};color:{}">{}</span>',
        bg, color, text
    )


# ─── Inline ───────────────────────────────────────────────────────────────────

class GroupMemberInline(admin.TabularInline):
    model           = GroupMember
    extra           = 0
    fields          = ['user', 'role', 'created_at']
    readonly_fields = ['created_at']
    raw_id_fields   = ['user']
    show_change_link = True


# ─── Group Admin ──────────────────────────────────────────────────────────────

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display    = [
        'name', 'group_type', 'member_count',
        'created_by_phone', 'store', 'is_active_badge', 'created_at',
    ]
    list_filter     = ['group_type', 'is_active']
    search_fields   = ['name', 'created_by__phone_number', 'store__name']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['created_by', 'store']
    raw_id_fields   = ['created_by', 'store']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines         = [GroupMemberInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _member_count=Count('members', distinct=True)
        )

    @admin.display(description='Members', ordering='_member_count')
    def member_count(self, obj):
        return obj._member_count

    @admin.display(description='Creator', ordering='created_by__phone_number')
    def created_by_phone(self, obj):
        return obj.created_by.phone_number

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Inactive', '#e2e3e5', '#383d41')


# ─── Group Member Admin ───────────────────────────────────────────────────────

@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display    = ['user', 'group', 'role', 'created_at']
    list_filter     = ['role']
    search_fields   = ['user__phone_number', 'group__name']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['user', 'group']
    raw_id_fields   = ['user', 'group']
    readonly_fields = ['created_at', 'updated_at']


# ─── Group Shared Product Admin ───────────────────────────────────────────────

@admin.register(GroupSharedProduct)
class GroupSharedProductAdmin(admin.ModelAdmin):
    list_display    = [
        'group', 'product', 'shared_by_phone',
        'is_finalized_badge', 'created_at',
    ]
    list_filter     = ['is_finalized']
    search_fields   = ['group__name', 'product__name', 'shared_by__phone_number']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['group', 'product', 'shared_by']
    raw_id_fields   = ['group', 'product', 'shared_by', 'finalized_by']
    readonly_fields = ['id', 'created_at', 'updated_at']

    @admin.display(description='Shared By', ordering='shared_by__phone_number')
    def shared_by_phone(self, obj):
        return obj.shared_by.phone_number

    @admin.display(description='Finalized', ordering='is_finalized')
    def is_finalized_badge(self, obj):
        if obj.is_finalized:
            return _badge('Finalized', '#d4edda', '#155724')
        return _badge('Pending', '#fff3cd', '#856404')


# ─── Group Message Admin ──────────────────────────────────────────────────────

@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display    = ['group', 'sender_phone', 'content_preview', 'created_at']
    search_fields   = ['group__name', 'sender__phone_number', 'content']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['group', 'sender']
    raw_id_fields   = ['group', 'sender']
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='Sender', ordering='sender__phone_number')
    def sender_phone(self, obj):
        return obj.sender.phone_number

    @admin.display(description='Message')
    def content_preview(self, obj):
        return obj.content[:60] + '…' if len(obj.content) > 60 else obj.content
