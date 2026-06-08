"""
NearKart — Group Chat WebSocket Consumer
ws://host/ws/groups/<uuid>/?token=<jwt>

Client sends:  {"type": "group_message", "content": "Hello group!"}
Server pushes: {serialized GroupMessage}
"""
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Group, GroupMessage
from .services import GroupService

logger = logging.getLogger(__name__)


class GroupConsumer(AsyncJsonWebsocketConsumer):

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def connect(self):
        user = self.scope.get('user')
        if not user or not getattr(user, 'id', None):
            await self.close(code=4001)
            return

        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.user = user

        group = await self._get_group()
        if not group:
            await self.close(code=4003)
            return
        self.group = group

        self.channel_group_name = f'group_{self.group_id}'
        await self.channel_layer.group_add(self.channel_group_name, self.channel_name)
        await self.accept()
        logger.info(f'WS group connected: {user.phone_number} → group {self.group_id}')

    async def disconnect(self, code):
        if hasattr(self, 'channel_group_name'):
            await self.channel_layer.group_discard(self.channel_group_name, self.channel_name)

    async def receive_json(self, content):
        msg_type = content.get('type')
        if msg_type != 'group_message':
            return

        text = (content.get('content') or '').strip()
        if not text:
            return

        message = await self._save_message(text)
        serialized = self._serialize(message)

        await self.channel_layer.group_send(
            self.channel_group_name,
            {'type': 'group_message', 'message': serialized},
        )

    # ── event handler ────────────────────────────────────────────────────────

    async def group_message(self, event):
        await self.send_json(event['message'])

    # ── helpers ──────────────────────────────────────────────────────────────

    @database_sync_to_async
    def _get_group(self):
        try:
            group = Group.objects.select_related('created_by').get(id=self.group_id, is_active=True)
        except Group.DoesNotExist:
            return None
        if not GroupService.is_member(group, self.user):
            return None
        return group

    @database_sync_to_async
    def _save_message(self, text):
        return GroupMessage.objects.create(
            group=self.group,
            sender=self.user,
            content=text,
        )

    @staticmethod
    def _serialize(message):
        return {
            'id':               str(message.id),
            'group_id':         str(message.group_id),
            'sender_id':        str(message.sender_id),
            'sender_name':      message.sender.full_name or '',
            'sender_profile_id': message.sender.profile_id or '',
            'content':          message.content,
            'created_at':       message.created_at.isoformat(),
        }
