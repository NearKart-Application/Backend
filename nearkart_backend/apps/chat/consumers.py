"""
NearKart — Chat WebSocket Consumer
ws://host/ws/conversations/<uuid>/?token=<jwt>

Client sends:  {"type": "chat_message", "content": "Hello!"}
Server pushes: {serialized Message object}
"""
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.blacklist.services import BlacklistService
from .models import Conversation
from .services import ConversationService, FCMService

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def connect(self):
        user = self.scope.get('user')
        if not user or not getattr(user, 'id', None):
            await self.close(code=4001)
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.user = user

        conversation = await self._get_conversation()
        if not conversation:
            await self.close(code=4003)
            return
        self.conversation = conversation

        self.group_name = f'conversation_{self.conversation_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f'WS connected: {user.phone_number} → conv {self.conversation_id}')

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        msg_type = content.get('type')
        if msg_type != 'chat_message':
            return

        text = (content.get('content') or '').strip()
        if not text:
            return

        message = await self._save_message(text)
        serialized = self._serialize(message)

        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat_message', 'message': serialized},
        )

        # Push notification to recipient (async, best-effort)
        await self._push_to_recipient(text)

    # ── event handler (called by channel layer group_send) ──────────────────

    async def chat_message(self, event):
        await self.send_json(event['message'])

    # ── helpers (DB) ─────────────────────────────────────────────────────────

    @database_sync_to_async
    def _get_conversation(self):
        try:
            conv = (
                Conversation.objects
                .select_related('store__owner', 'customer')
                .get(id=self.conversation_id)
            )
        except Conversation.DoesNotExist:
            return None
        if not ConversationService.user_belongs_to_conversation(self.user, conv):
            return None
        # Blocked customer cannot connect to this store's conversations
        if self.user.role == 'customer' and BlacklistService.is_blocked(conv.store, self.user):
            return None
        return conv

    @database_sync_to_async
    def _save_message(self, text):
        return ConversationService.save_message(
            conversation=self.conversation,
            sender=self.user,
            content=text,
        )

    @database_sync_to_async
    def _push_to_recipient(self, text):
        conv = Conversation.objects.select_related(
            'customer', 'store__owner',
        ).get(id=self.conversation_id)

        is_customer_sending = (self.user.id == conv.customer_id)
        recipient = conv.store.owner if is_customer_sending else conv.customer
        sender_label = 'Customer' if is_customer_sending else conv.store.name

        FCMService.send_push(
            recipient=recipient,
            title=f'New message from {sender_label}',
            body=text[:100],
            data={'conversation_id': str(self.conversation_id)},
        )

    @staticmethod
    def _serialize(message):
        return {
            'id':              str(message.id),
            'conversation_id': str(message.conversation_id),
            'sender_id':       str(message.sender_id),
            'sender_phone':    message.sender.phone_number,
            'sender_role':     message.sender.role,
            'content':         message.content,
            'message_type':    message.message_type,
            'media_url':       message.media_url,
            'ref_id':          str(message.ref_id) if message.ref_id else None,
            'is_read':         message.is_read,
            'created_at':      message.created_at.isoformat(),
        }
