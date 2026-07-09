"""
NearKart — Chat Admin
Shopify-grade admin for Conversation and Message.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Conversation, Message


# ─── Helper ───────────────────────────────────────────────────────────────────

def _badge(text, bg, color):
    return format_html(
        '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:{};color:{}">{}</span>',
        bg, color, text
    )


# ─── Conversation Admin ───────────────────────────────────────────────────────

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display    = [
        'customer_phone', 'store', 'last_message_at',
        'unread_count_customer', 'unread_count_vendor', 'is_active_badge',
    ]
    list_filter     = ['is_active']
    search_fields   = ['customer__phone_number', 'store__name']
    ordering        = ['-last_message_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    show_full_result_count = False
    list_select_related    = ['customer', 'store']
    raw_id_fields   = ['customer', 'store']
    readonly_fields = ['id', 'created_at', 'updated_at']

    @admin.display(description='Customer', ordering='customer__phone_number')
    def customer_phone(self, obj):
        return obj.customer.phone_number

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return _badge('Active', '#d4edda', '#155724')
        return _badge('Closed', '#e2e3e5', '#383d41')


# ─── Message Admin ────────────────────────────────────────────────────────────

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display    = [
        'sender_phone', 'conversation', 'message_type',
        'content_preview', 'is_read_badge', 'created_at',
    ]
    list_filter     = ['message_type', 'is_read']
    search_fields   = ['sender__phone_number', 'content']
    ordering        = ['-created_at']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['sender', 'conversation']
    raw_id_fields   = ['conversation', 'sender']
    readonly_fields = ['id', 'created_at', 'updated_at']

    @admin.display(description='Sender', ordering='sender__phone_number')
    def sender_phone(self, obj):
        return obj.sender.phone_number

    @admin.display(description='Message')
    def content_preview(self, obj):
        if len(obj.content) > 60:
            return obj.content[:60] + '…'
        return obj.content or '(media)'

    @admin.display(description='Read', ordering='is_read')
    def is_read_badge(self, obj):
        if obj.is_read:
            return _badge('Read', '#d4edda', '#155724')
        return _badge('Unread', '#fff3cd', '#856404')
