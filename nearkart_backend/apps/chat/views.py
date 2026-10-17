"""
NearKart — Chat REST Views
POST  /api/v1/conversations/start/              → get-or-create conversation
GET   /api/v1/conversations/                    → list my conversations
GET   /api/v1/conversations/<id>/messages/      → message history (paginated)
POST  /api/v1/conversations/<id>/messages/      → send a message (text or image)
POST  /api/v1/conversations/<id>/upload/        → upload a chat image → {url, message_type}
PATCH /api/v1/conversations/<id>/read/          → mark conversation as read
"""
import logging
import os
import uuid as _uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from drf_spectacular.utils import (
    OpenApiExample, OpenApiParameter, OpenApiResponse,
    extend_schema, inline_serializer,
)
from rest_framework import serializers as s
from rest_framework import status
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stores.models import Store
from apps.blacklist.services import BlacklistService
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from .services import ConversationService

logger = logging.getLogger(__name__)
_TAG = 'Chat'


class ConversationStartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Start or get a conversation with a store',
        description=(
            'Creates a new conversation between the authenticated user and a store, '
            'or returns the existing one if it already exists.\n\n'
            'Either the customer OR the vendor can initiate — both get the same conversation.\n\n'
            '**Vendor calling this** → returns their own conversation with a customer '
            '(must provide customer_id).\n\n'
            '**Customer calling this** → creates/gets conversation with the store '
            '(provide store_id only).'
        ),
        request=inline_serializer('StartConversationRequest', fields={
            'store_id':    s.UUIDField(help_text='Store UUID to chat with'),
            'customer_id': s.UUIDField(required=False,
                               help_text='Customer UUID (vendor use only — to open a specific conversation)'),
        }),
        responses={
            200: ConversationSerializer,
            201: ConversationSerializer,
            400: OpenApiResponse(description='Missing store_id or invalid UUID'),
            404: OpenApiResponse(description='Store not found'),
        },
        examples=[
            OpenApiExample('Customer starts chat', request_only=True,
                           value={'store_id': '6c8adfdd-a788-4661-88e7-0768a037745e'}),
        ],
    )
    def post(self, request):
        user = request.user

        # Determine customer
        if user.role == 'vendor':
            customer_id = request.data.get('customer_id')
            if not customer_id:
                return Response(
                    {'error': 'validation_error', 'message': 'customer_id is required for vendors.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from apps.auth_app.models import User
            try:
                customer = User.objects.get(id=customer_id, role='customer')
            except User.DoesNotExist:
                return Response(
                    {'error': 'not_found', 'message': 'Customer not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not hasattr(user, 'store'):
                return Response(
                    {'error': 'validation_error', 'message': 'You do not have a store.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            store = user.store
        else:
            customer = user
            store_id = request.data.get('store_id')
            if not store_id:
                return Response(
                    {'error': 'validation_error', 'message': 'store_id is required.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                store = Store.objects.get(id=store_id, is_active=True)
            except Store.DoesNotExist:
                return Response(
                    {'error': 'not_found', 'message': 'Store not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if BlacklistService.is_blocked(store, customer):
                return Response(
                    {'error': 'blacklisted', 'message': 'You cannot start a conversation with this store.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        conversation, created = ConversationService.get_or_create(customer=customer, store=store)
        resp_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            ConversationSerializer(conversation, context={'request': request}).data,
            status=resp_status,
        )


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='List my conversations (sorted by latest message)',
        description=(
            'Returns all active conversations for the current user.\n\n'
            '**Customer** sees all conversations they started with stores.\n\n'
            '**Vendor** sees all conversations for their store.'
        ),
        responses={200: ConversationSerializer(many=True)},
    )
    def get(self, request):
        qs = ConversationService.list_for_user(request.user)
        return Response(
            ConversationSerializer(qs, many=True, context={'request': request}).data
        )


class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Get message history for a conversation',
        description=(
            'Returns up to 50 messages, newest last.\n\n'
            'For older messages, pass `?before=<message_id>` to paginate backwards.'
        ),
        parameters=[
            OpenApiParameter('before', str,
                description='Message UUID — returns messages older than this one',
                required=False),
        ],
        responses={200: MessageSerializer(many=True)},
    )
    def get(self, request, conversation_id):
        conversation = self._get_or_403(conversation_id, request.user)
        if isinstance(conversation, Response):
            return conversation
        before_id = request.query_params.get('before')
        messages = ConversationService.get_messages(conversation, before_id=before_id)
        return Response(MessageSerializer(messages, many=True).data)

    @extend_schema(
        tags=[_TAG],
        summary='Send a message in a conversation',
        request=inline_serializer('SendMessageRequest', fields={
            'content':      s.CharField(required=False, help_text='Message text (required for text messages)'),
            'message_type': s.ChoiceField(choices=['text', 'image'], default='text'),
            'media_url':    s.URLField(required=False, help_text='Image URL (required for image messages)'),
        }),
        responses={201: MessageSerializer},
    )
    def post(self, request, conversation_id):
        conversation = self._get_or_403(conversation_id, request.user)
        if isinstance(conversation, Response):
            return conversation
        content      = (request.data.get('content') or '').strip()
        message_type = request.data.get('message_type', Message.TYPE_TEXT)
        media_url    = (request.data.get('media_url') or '').strip()
        if message_type not in (Message.TYPE_TEXT, Message.TYPE_IMAGE, Message.TYPE_PRODUCT_REF, Message.TYPE_VIDEO_REF):
            message_type = Message.TYPE_TEXT
        if message_type == Message.TYPE_TEXT and not content:
            return Response(
                {'error': 'validation_error', 'message': 'content is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        msg = ConversationService.save_message(
            conversation, request.user, content,
            message_type=message_type, media_url=media_url,
        )
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    def _get_or_403(self, conversation_id, user):
        try:
            conv = Conversation.objects.select_related(
                'customer', 'store__owner',
            ).get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Conversation not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not ConversationService.user_belongs_to_conversation(user, conv):
            return Response(
                {'error': 'permission_denied', 'message': 'You are not part of this conversation.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return conv


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Mark conversation as read (reset my unread count)',
        request=None,
        responses={200: OpenApiResponse(
            response=inline_serializer('MarkReadResponse', fields={
                'message': s.CharField(),
            })
        )},
    )
    def patch(self, request, conversation_id):
        try:
            conv = Conversation.objects.select_related(
                'customer', 'store__owner',
            ).get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Conversation not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not ConversationService.user_belongs_to_conversation(request.user, conv):
            return Response(
                {'error': 'permission_denied', 'message': 'You are not part of this conversation.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        ConversationService.mark_read(conv, request.user)
        return Response({'message': 'Marked as read.'})


class ChatMediaUploadView(APIView):
    """Upload an image for use in a chat message. Returns the URL to embed."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    _ALLOWED_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    _MAX_BYTES = 10 * 1024 * 1024  # 10 MB

    @extend_schema(
        tags=[_TAG],
        summary='Upload a chat image',
        description='Upload a JPEG/PNG/WebP/GIF image (≤ 10 MB). Returns `{url, message_type}` to send as a chat message.',
        request=inline_serializer('ChatUploadRequest', fields={'image': s.ImageField()}),
        responses={
            201: inline_serializer('ChatUploadResponse', fields={
                'url':          s.URLField(),
                'message_type': s.CharField(),
            }),
            400: OpenApiResponse(description='Missing or invalid image'),
            403: OpenApiResponse(description='Not a member of this conversation'),
        },
    )
    def post(self, request, conversation_id):
        try:
            conv = Conversation.objects.select_related('customer', 'store__owner').get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not ConversationService.user_belongs_to_conversation(request.user, conv):
            return Response({'error': 'permission_denied', 'message': 'You are not part of this conversation.'}, status=status.HTTP_403_FORBIDDEN)

        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'validation_error', 'message': 'image file is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if image.size > self._MAX_BYTES:
            return Response({'error': 'validation_error', 'message': 'Image must be ≤ 10 MB.'}, status=status.HTTP_400_BAD_REQUEST)
        ext = os.path.splitext(image.name)[1].lower()
        if ext not in self._ALLOWED_EXTS:
            return Response({'error': 'validation_error', 'message': 'Only JPEG, PNG, WebP, or GIF images are allowed.'}, status=status.HTTP_400_BAD_REQUEST)

        filename = f'chat/{_uuid.uuid4()}{ext}'
        saved_path = default_storage.save(filename, ContentFile(image.read()))
        url = default_storage.url(saved_path)
        return Response({'url': url, 'message_type': 'image'}, status=status.HTTP_201_CREATED)


class MessageDeleteView(APIView):
    """DELETE /conversations/<conv_id>/messages/<msg_id>/ — soft-delete own message."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, conversation_id, message_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        if not ConversationService.user_belongs_to_conversation(request.user, conv):
            return Response({'error': 'permission_denied'}, status=403)
        try:
            msg = Message.objects.get(id=message_id, conversation=conv)
        except Message.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        if msg.sender_id != request.user.id:
            return Response({'error': 'permission_denied', 'message': 'Can only delete your own messages.'}, status=403)
        msg.is_deleted = True
        msg.content = ''
        msg.save(update_fields=['is_deleted', 'content', 'updated_at'])
        return Response({'id': str(msg.id), 'is_deleted': True})


class MessageReactionView(APIView):
    """POST/DELETE /conversations/<conv_id>/messages/<msg_id>/react/ — toggle reaction."""
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id, message_id):
        from .models import MessageReaction
        emoji = (request.data.get('emoji') or '').strip()
        if not emoji:
            return Response({'error': 'validation_error', 'message': 'emoji required.'}, status=400)
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        if not ConversationService.user_belongs_to_conversation(request.user, conv):
            return Response({'error': 'permission_denied'}, status=403)
        try:
            msg = Message.objects.get(id=message_id, conversation=conv)
        except Message.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        reaction, created = MessageReaction.objects.update_or_create(
            message=msg, user=request.user,
            defaults={'emoji': emoji},
        )
        return Response({'id': str(reaction.id), 'emoji': reaction.emoji, 'created': created},
                        status=201 if created else 200)

    def delete(self, request, conversation_id, message_id):
        from .models import MessageReaction
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'not_found'}, status=404)
        if not ConversationService.user_belongs_to_conversation(request.user, conv):
            return Response({'error': 'permission_denied'}, status=403)
        MessageReaction.objects.filter(message_id=message_id, user=request.user).delete()
        return Response(status=204)
