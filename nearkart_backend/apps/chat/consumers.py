"""
NearKart — Chat WebSocket Consumer
ws://host/ws/conversations/<uuid>/?token=<jwt>

Client sends:  {"type": "chat_message", "content": "Hello!"}
               {"type": "refresh_token", "token": "<new_access_token>"}
Server pushes: {serialized Message object}
"""
import logging
from datetime import datetime, timezone as dt_timezone
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.blacklist.services import BlacklistService
from apps.notifications.services import NotificationService
from .models import Conversation
from .services import ConversationService

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

        if msg_type == 'refresh_token':
            # Client proactively sends a new access token before the old one expires.
            # Re-validate and update the stored user so messages after the refresh
            # are still authorized. Close with 4001 if the new token is invalid.
            new_token = (content.get('token') or '').strip()
            refreshed_user = await self._resolve_token(new_token)
            if not refreshed_user or refreshed_user.id != self.user.id:
                await self.close(code=4001)
                return
            self.user = refreshed_user
            await self.send_json({'type': 'token_refreshed', 'status': 'ok'})
            return

        # Reject messages from connections whose access token has expired.
        if await self._token_expired():
            await self.close(code=4001)
            return

        if msg_type == 'typing':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type':      'typing_event',
                    'sender_id': str(self.user.id),
                    'is_typing': bool(content.get('is_typing', False)),
                },
            )
            return

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

    # ── event handlers (called by channel layer group_send) ─────────────────

    async def chat_message(self, event):
        await self.send_json(event['message'])

    async def typing_event(self, event):
        # Don't echo typing back to the sender
        if event['sender_id'] == str(self.user.id):
            return
        await self.send_json({
            'type':      'typing',
            'is_typing': event['is_typing'],
        })

    # ── helpers (DB) ─────────────────────────────────────────────────────────

    @database_sync_to_async
    def _resolve_token(self, token_key: str):
        """Validate a JWT access token and return the matching User, or None."""
        if not token_key:
            return None
        try:
            token = AccessToken(token_key)
            from apps.auth_app.models import User
            return User.objects.get(id=token['user_id'])
        except (TokenError, Exception):
            return None

    async def _token_expired(self) -> bool:
        """Return True if the original connect-time token has passed its expiry."""
        token_key = parse_qs(self.scope.get('query_string', b'').decode()).get('token', [None])[0]
        if not token_key:
            return True
        try:
            token = AccessToken(token_key)
            exp = token.payload.get('exp', 0)
            return datetime.fromtimestamp(exp, tz=dt_timezone.utc) < datetime.now(tz=dt_timezone.utc)
        except TokenError:
            return True

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

        NotificationService.notify_new_message(
            recipient,
            sender_label,
            str(self.conversation_id),
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
