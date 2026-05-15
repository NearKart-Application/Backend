from django.contrib import admin

from .models import Group, GroupMember, GroupSharedProduct


class GroupMemberInline(admin.TabularInline):
    model       = GroupMember
    extra       = 0
    fields      = ['user', 'role', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display    = ['name', 'group_type', 'created_by', 'store', 'is_active', 'created_at']
    list_filter     = ['group_type', 'is_active']
    search_fields   = ['name', 'created_by__phone_number', 'store__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines         = [GroupMemberInline]


@admin.register(GroupSharedProduct)
class GroupSharedProductAdmin(admin.ModelAdmin):
    list_display    = ['group', 'product', 'shared_by', 'is_finalized', 'created_at']
    list_filter     = ['is_finalized']
    search_fields   = ['group__name', 'product__name', 'shared_by__phone_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
