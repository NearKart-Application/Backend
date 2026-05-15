"""
NearKart — FCM Push Notification Sender
Dev mode: logs only. Production: uses firebase_admin SDK.
"""
import logging

logger = logging.getLogger(__name__)


def _get_firebase_app():
    try:
        import firebase_admin
        return firebase_admin.get_app()
    except Exception:
        return None


def _is_dev_fcm() -> bool:
    return _get_firebase_app() is None


class FCMService:
    @staticmethod
    def send_push(recipient, title: str, body: str, data: dict | None = None):
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
