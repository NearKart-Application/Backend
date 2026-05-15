from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display  = ['id', 'customer', 'store', 'last_message_at',
                     'unread_count_customer', 'unread_count_vendor', 'is_active']
    list_filter   = ['is_active', 'store']
    search_fields = ['customer__phone_number', 'store__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display  = ['id', 'conversation', 'sender', 'message_type', 'is_read', 'created_at']
    list_filter   = ['message_type', 'is_read']
    search_fields = ['sender__phone_number', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at']
