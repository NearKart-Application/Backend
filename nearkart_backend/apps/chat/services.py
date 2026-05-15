"""
NearKart — Chat Services
ConversationService: create/get conversations, save messages, mark read
FCMService: push notifications for offline users (dev mode: mock)
"""
import logging

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from apps.auth_app.models import User
from apps.stores.models import Store
from .models import Conversation, Message

logger = logging.getLogger(__name__)

# ── Firebase init guard ──────────────────────────────────────────────────────
_firebase_app = None

def _get_firebase_app():
    global _firebase_app
    if _firebase_app:
        return _firebase_app
    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', '')
    if not cred_path or 'EXAMPLE' in cred_path.upper() or not cred_path.endswith('.json'):
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials as fb_creds
        cred = fb_creds.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        return _firebase_app
    except Exception as e:
        logger.warning(f'Firebase init failed: {e}')
        return None


def _is_dev_fcm():
    return _get_firebase_app() is None


# ── FCM Service ──────────────────────────────────────────────────────────────

class FCMService:
    @staticmethod
    def send_push(recipient: User, title: str, body: str, data: dict | None = None):
        tokens = list(
            recipient.device_tokens
            .filter(is_active=True)
            .values_list('fcm_token', flat=True)
        )
        if not tokens:
            return

        if _is_dev_fcm():
            logger.info(
                f'[FCM-DEV] → {recipient.phone_number} | '
                f'title="{title}" body="{body[:60]}" tokens={len(tokens)}'
            )
            return

        try:
            from firebase_admin import messaging
            messages = [
                messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data={k: str(v) for k, v in (data or {}).items()},
                    token=token,
                )
                for token in tokens
            ]
            resp = messaging.send_each(messages)
            logger.info(f'FCM sent {resp.success_count}/{len(tokens)} to {recipient.phone_number}')
        except Exception as e:
            logger.error(f'FCM push failed for {recipient.phone_number}: {e}')


# ── Conversation Service ─────────────────────────────────────────────────────

class ConversationService:

    @staticmethod
    def get_or_create(customer: User, store: Store) -> tuple[Conversation, bool]:
        return Conversation.objects.get_or_create(
            customer=customer,
            store=store,
        )

    @staticmethod
    def list_for_user(user: User):
        if user.role == 'vendor':
            if not hasattr(user, 'store'):
                return Conversation.objects.none()
            return (
                Conversation.objects
                .filter(store=user.store, is_active=True)
                .select_related('customer', 'store')
                .order_by('-last_message_at')
            )
        return (
            Conversation.objects
            .filter(customer=user, is_active=True)
            .select_related('customer', 'store')
            .order_by('-last_message_at')
        )

    @staticmethod
    def save_message(
        conversation: Conversation,
        sender: User,
        content: str,
        message_type: str = Message.TYPE_TEXT,
        media_url: str = '',
        ref_id=None,
    ) -> Message:
        msg = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            message_type=message_type,
            media_url=media_url,
            ref_id=ref_id,
        )
        # Update last_message_at and increment unread counter for the other party
        is_customer_sending = (sender.id == conversation.customer_id)
        if is_customer_sending:
            Conversation.objects.filter(id=conversation.id).update(
                last_message_at=timezone.now(),
                unread_count_vendor=F('unread_count_vendor') + 1,
            )
        else:
            Conversation.objects.filter(id=conversation.id).update(
                last_message_at=timezone.now(),
                unread_count_customer=F('unread_count_customer') + 1,
            )
        return msg

    @staticmethod
    def mark_read(conversation: Conversation, user: User):
        is_customer = (user.id == conversation.customer_id)
        if is_customer:
            Conversation.objects.filter(id=conversation.id).update(unread_count_customer=0)
            Message.objects.filter(
                conversation=conversation, is_read=False,
            ).exclude(sender=user).update(is_read=True)
        else:
            Conversation.objects.filter(id=conversation.id).update(unread_count_vendor=0)
            Message.objects.filter(
                conversation=conversation, is_read=False,
            ).exclude(sender=user).update(is_read=True)

    @staticmethod
    def get_messages(conversation: Conversation, before_id=None, limit=50):
        qs = Message.objects.filter(conversation=conversation).order_by('-created_at')
        if before_id:
            try:
                pivot = Message.objects.get(id=before_id)
                qs = qs.filter(created_at__lt=pivot.created_at)
            except Message.DoesNotExist:
                pass
        return list(reversed(qs[:limit]))

    @staticmethod
    def user_belongs_to_conversation(user: User, conversation: Conversation) -> bool:
        if user.id == conversation.customer_id:
            return True
        if user.role == 'vendor' and hasattr(user, 'store'):
            return conversation.store_id == user.store.id
        return False
