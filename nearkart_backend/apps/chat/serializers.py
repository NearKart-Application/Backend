"""
NearKart — Chat Serializers
"""
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_phone = serializers.SerializerMethodField()
    sender_role  = serializers.SerializerMethodField()

    class Meta:
        model  = Message
        fields = [
            'id', 'conversation_id', 'sender_id', 'sender_phone', 'sender_role',
            'content', 'message_type', 'media_url', 'ref_id',
            'is_read', 'created_at',
        ]

    @extend_schema_field(serializers.CharField())
    def get_sender_phone(self, obj):
        return obj.sender.phone_number

    @extend_schema_field(serializers.CharField())
    def get_sender_role(self, obj):
        return obj.sender.role


class ConversationSerializer(serializers.ModelSerializer):
    store_name       = serializers.CharField(source='store.name', read_only=True)
    store_id         = serializers.UUIDField(source='store.id', read_only=True)
    customer_phone   = serializers.CharField(source='customer.phone_number', read_only=True)
    my_unread_count  = serializers.SerializerMethodField()
    last_message     = serializers.SerializerMethodField()

    class Meta:
        model  = Conversation
        fields = [
            'id', 'store_id', 'store_name', 'customer_phone',
            'my_unread_count', 'last_message', 'last_message_at',
            'is_active', 'created_at',
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_my_unread_count(self, obj):
        user = self.context['request'].user
        if user.id == obj.customer_id:
            return obj.unread_count_customer
        return obj.unread_count_vendor

    @extend_schema_field(MessageSerializer())
    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if not msg:
            return None
        return MessageSerializer(msg).data
