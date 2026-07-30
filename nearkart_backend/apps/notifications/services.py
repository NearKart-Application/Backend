"""
NearKart — Notification Services
SMSService: OTP delivery via Twilio
NotificationService: in-app inbox + FCM push
"""
import logging
from django.conf import settings

from .fcm import FCMService
from .models import Notification, NotificationType

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    def send(recipient, notification_type: str, title: str, body: str, data: dict = None) -> Notification:
        notif = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data or {},
        )
        FCMService.send_push(recipient, title, body, data)
        return notif

    @staticmethod
    def send_bulk(recipients, notification_type: str, title: str, body: str, data: dict = None):
        for recipient in recipients:
            NotificationService.send(recipient, notification_type, title, body, data)

    # ── Helpers — one method per event ──────────────────────────────────────

    @staticmethod
    def notify_new_message(recipient, sender_label: str, conversation_id: str):
        NotificationService.send(
            recipient, NotificationType.NEW_MESSAGE,
            title=f'New message from {sender_label}',
            body='You have a new message.',
            data={'conversation_id': conversation_id},
        )

    @staticmethod
    def notify_reservation_created(vendor, customer_name: str, reservation_id: str, product_name: str):
        NotificationService.send(
            vendor, NotificationType.RESERVATION_CREATED,
            title='New Reservation',
            body=f'{customer_name} reserved {product_name}.',
            data={'reservation_id': reservation_id, 'notification_type': 'reservation', 'type': 'reservation'},
        )

    @staticmethod
    def notify_reservation_confirmed(customer, store_name: str, reservation_id: str):
        NotificationService.send(
            customer, NotificationType.RESERVATION_CONFIRMED,
            title='Reservation Confirmed',
            body=f'Your reservation at {store_name} has been confirmed.',
            data={'reservation_id': reservation_id, 'notification_type': 'reservation', 'type': 'reservation'},
        )

    @staticmethod
    def notify_reservation_cancelled(customer, store_name: str, reservation_id: str):
        NotificationService.send(
            customer, NotificationType.RESERVATION_CANCELLED,
            title='Reservation Cancelled',
            body=f'Your reservation at {store_name} has been cancelled.',
            data={'reservation_id': reservation_id, 'notification_type': 'reservation', 'type': 'reservation'},
        )

    @staticmethod
    def notify_reservation_expired(customer, store_name: str, reservation_id: str):
        NotificationService.send(
            customer, NotificationType.RESERVATION_EXPIRED,
            title='Reservation Expired',
            body=f'Your hold at {store_name} has expired.',
            data={'reservation_id': reservation_id, 'notification_type': 'reservation', 'type': 'reservation'},
        )

    @staticmethod
    def notify_reservation_expiring_soon(
        customer, store_name: str, reservation_id: str, product_name: str,
        time_label: str = 'tomorrow', time_body: str = '~24 hours',
    ):
        NotificationService.send(
            customer, NotificationType.RESERVATION_EXPIRING_SOON,
            title=f'Hold expiring {time_label}',
            body=f'Your hold on {product_name} at {store_name} expires in {time_body}.',
            data={'reservation_id': reservation_id, 'notification_type': 'reservation', 'type': 'reservation'},
        )

    @staticmethod
    def notify_new_follower(vendor, follower_name: str):
        NotificationService.send(
            vendor, NotificationType.NEW_FOLLOWER,
            title='New Follower',
            body=f'{follower_name} is now following your store.',
        )

    @staticmethod
    def notify_store_opened(followers, store_name: str, store_id: str):
        NotificationService.send_bulk(
            followers, NotificationType.STORE_OPENED,
            title=f'{store_name} is now open!',
            body='A store you follow just opened. Check it out.',
            data={'store_id': store_id},
        )

    @staticmethod
    def notify_new_offer(followers, store_name: str, offer_label: str, store_id: str):
        NotificationService.send_bulk(
            followers, NotificationType.NEW_OFFER,
            title=f'New offer from {store_name}',
            body=offer_label,
            data={'store_id': store_id},
        )

    @staticmethod
    def notify_video_liked(vendor, liker_name: str, video_title: str, video_id: str):
        NotificationService.send(
            vendor, NotificationType.VIDEO_LIKED,
            title='New Like',
            body=f'{liker_name} liked your video "{video_title}".',
            data={'video_id': video_id},
        )

    @staticmethod
    def notify_video_ready(vendor, video_title: str, video_id: str):
        NotificationService.send(
            vendor, NotificationType.VIDEO_READY,
            title='Video Ready',
            body=f'Your video "{video_title}" is ready to view.',
            data={'video_id': video_id},
        )

    @staticmethod
    def notify_video_expiring_soon(vendor, video_title: str, video_id: str, expires_at: str):
        NotificationService.send(
            vendor, NotificationType.VIDEO_EXPIRING_SOON,
            title='Video Expiring in 2 Days',
            body=f'Your video "{video_title}" will be deleted in 2 days. Download it now if you want to keep a copy.',
            data={'video_id': video_id, 'expires_at': expires_at, 'action': 'download_prompt'},
        )

    @staticmethod
    def notify_wallet_topup(vendor, amount: str):
        NotificationService.send(
            vendor, NotificationType.WALLET_TOPUP,
            title='Wallet Topped Up',
            body=f'₹{amount} has been added to your wallet.',
        )

    @staticmethod
    def notify_subscription_expiring(vendor, store_name: str, days_left: int):
        NotificationService.send(
            vendor, NotificationType.SUBSCRIPTION_EXPIRING,
            title='Subscription Expiring Soon',
            body=f'Your {store_name} subscription expires in {days_left} day(s). Renew now.',
        )

    @staticmethod
    def notify_subscription_expired(vendor, store_name: str):
        NotificationService.send(
            vendor, NotificationType.SUBSCRIPTION_EXPIRED,
            title='Subscription Expired',
            body=f'Your {store_name} subscription has expired. Renew to continue selling.',
        )

    @staticmethod
    def notify_group_added(user, group_name: str, group_id: str, added_by: str):
        NotificationService.send(
            user, NotificationType.GROUP_ADDED,
            title='Added to Group',
            body=f'{added_by} added you to "{group_name}".',
            data={'group_id': group_id},
        )

    @staticmethod
    def notify_group_removed(user, group_name: str, group_id: str):
        NotificationService.send(
            user, NotificationType.GROUP_REMOVED,
            title='Removed from Group',
            body=f'You have been removed from "{group_name}".',
            data={'group_id': group_id},
        )

    @staticmethod
    def notify_group_product_shared(members, group_name: str, group_id: str, sharer_name: str, product_name: str):
        NotificationService.send_bulk(
            members, NotificationType.GROUP_PRODUCT_SHARED,
            title='New Product Shared',
            body=f'{sharer_name} shared "{product_name}" in {group_name}.',
            data={'group_id': group_id},
        )

    @staticmethod
    def notify_group_product_finalized(members, group_name: str, group_id: str, product_name: str):
        NotificationService.send_bulk(
            members, NotificationType.GROUP_PRODUCT_FINALIZED,
            title='Product Finalized',
            body=f'"{product_name}" was chosen as the final pick in {group_name}.',
            data={'group_id': group_id},
        )

    @staticmethod
    def notify_group_admin_promoted(user, group_name: str, group_id: str):
        NotificationService.send(
            user, NotificationType.GROUP_ADMIN_PROMOTED,
            title='You are now a Group Admin',
            body=f'You have been made an admin of "{group_name}".',
            data={'group_id': group_id},
        )

    @staticmethod
    def notify_invoice_received(customer, store_name: str, invoice_id: str, total: str):
        NotificationService.send(
            customer, NotificationType.INVOICE_RECEIVED,
            title=f'Invoice from {store_name}',
            body=f'You received an invoice for ₹{total}.',
            data={'invoice_id': invoice_id},
        )

    @staticmethod
    def notify_new_review(vendor, store_name: str, rating: int, store_id: str):
        stars = '★' * rating + '☆' * (5 - rating)
        NotificationService.send(
            vendor, NotificationType.NEW_REVIEW,
            title=f'New Review — {store_name}',
            body=f'A customer left a {stars} review for your store.',
            data={'store_id': store_id},
        )

    @staticmethod
    def notify_price_drop(customer, product_name: str, product_id: str, old_price: str, new_price: str):
        NotificationService.send(
            customer, NotificationType.PRICE_DROP_ALERT,
            title=f'Price Drop on {product_name}!',
            body=f'{product_name} dropped from ₹{old_price} to ₹{new_price}. Tap to grab it now.',
            data={'product_id': product_id, 'old_price': old_price, 'new_price': new_price},
        )

    @staticmethod
    def notify_referral_reward(vendor, amount: str, reward_type: str):
        type_label = 'vendor signup' if reward_type == 'vendor' else 'customer reservation'
        NotificationService.send(
            vendor, NotificationType.REFERRAL_REWARD,
            title='Referral Reward Earned!',
            body=f'You earned ₹{amount} for a {type_label} referral. Wallet credited.',
            data={'amount': amount, 'reward_type': reward_type},
        )

    @staticmethod
    def notify_vendor_coupon(vendor, plan_display: str, discount_percent: int, coupon_code: str):
        """Sent to vendor when admin creates a targeted coupon for their store."""
        if discount_percent == 100:
            body = f'Subscribe to {plan_display} for FREE using code {coupon_code}. Tap to activate.'
        else:
            body = f'Get {discount_percent}% off on {plan_display}! Use code {coupon_code}. Tap to activate.'
        NotificationService.send(
            vendor, NotificationType.VENDOR_COUPON,
            title='Special Offer Just For You!',
            body=body,
            data={'coupon_code': coupon_code, 'action': 'open_billing'},
        )


class SMSService:

    @staticmethod
    def send_otp(phone_number: str, otp: str) -> bool:
        """
        Sends OTP SMS via Twilio. Returns True on success.
        Logs and returns False on failure without raising.
        """
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=f'Your NearSpot OTP is {otp}. Valid for 5 minutes. Do not share.',
                from_=settings.TWILIO_FROM_NUMBER,
                to=phone_number,
            )
            logger.info(f'OTP SMS sent to {phone_number}')
            return True
        except Exception as e:
            logger.error(f'Failed to send OTP SMS to {phone_number}: {e}')
            return False

    @staticmethod
    def send_voice_otp(phone_number: str, otp: str) -> bool:
        """Delivers OTP via a Twilio voice call with TwiML read-aloud message."""
        try:
            from twilio.rest import Client
            from twilio.twiml.voice_response import VoiceResponse
            spaced_otp = '  '.join(otp)
            twiml = VoiceResponse()
            twiml.say(
                f'Hello. Your NearSpot verification code is {spaced_otp}. '
                f'I repeat, {spaced_otp}. Goodbye.',
                voice='alice',
                language='en-IN',
            )
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.calls.create(
                twiml=str(twiml),
                from_=settings.TWILIO_FROM_NUMBER,
                to=phone_number,
            )
            logger.info(f'Voice OTP call placed to {phone_number}')
            return True
        except Exception as e:
            logger.error(f'Failed to place voice OTP call to {phone_number}: {e}')
            return False
