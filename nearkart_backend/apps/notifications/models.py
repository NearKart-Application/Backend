"""
NearKart — Notifications Models
In-app notification inbox. Push is handled by FCMService.
"""
from django.db import models
from django.conf import settings

from core.models import BaseModel


class NotificationType(models.TextChoices):
    # Chat
    NEW_MESSAGE             = 'new_message',             'New Message'
    # Reservations
    RESERVATION_CREATED        = 'reservation_created',        'Reservation Created'
    RESERVATION_CONFIRMED      = 'reservation_confirmed',      'Reservation Confirmed'
    RESERVATION_CANCELLED      = 'reservation_cancelled',      'Reservation Cancelled'
    RESERVATION_EXPIRED        = 'reservation_expired',        'Reservation Expired'
    RESERVATION_EXPIRING_SOON  = 'reservation_expiring_soon',  'Reservation Expiring Soon'
    # Store
    NEW_FOLLOWER            = 'new_follower',            'New Follower'
    NEW_REVIEW              = 'new_review',              'New Review'
    STORE_OPENED            = 'store_opened',            'Store Opened'
    NEW_OFFER               = 'new_offer',               'New Offer'
    # Videos
    VIDEO_LIKED             = 'video_liked',             'Video Liked'
    VIDEO_READY             = 'video_ready',             'Video Ready'
    VIDEO_EXPIRING_SOON     = 'video_expiring_soon',     'Video Expiring Soon'
    # Billing
    WALLET_TOPUP            = 'wallet_topup',            'Wallet Top-Up'
    SUBSCRIPTION_EXPIRING   = 'subscription_expiring',   'Subscription Expiring'
    SUBSCRIPTION_EXPIRED    = 'subscription_expired',    'Subscription Expired'
    # Groups
    GROUP_ADDED             = 'group_added',             'Added to Group'
    GROUP_REMOVED           = 'group_removed',           'Removed from Group'
    GROUP_PRODUCT_SHARED    = 'group_product_shared',    'Product Shared in Group'
    GROUP_PRODUCT_FINALIZED = 'group_product_finalized', 'Product Finalized in Group'
    GROUP_ADMIN_PROMOTED    = 'group_admin_promoted',    'Promoted to Group Admin'
    # Invoices
    INVOICE_RECEIVED        = 'invoice_received',        'Invoice Received'
    # Loyalty
    LOYALTY                 = 'loyalty',                 'Loyalty Points'
    # Vendor-specific coupons
    VENDOR_COUPON           = 'vendor_coupon',           'Vendor Coupon'
    # Analytics
    WEEKLY_DIGEST           = 'weekly_digest',           'Weekly Digest'
    # Price alerts
    PRICE_DROP_ALERT        = 'price_drop_alert',        'Price Drop Alert'
    # Inventory
    LOW_STOCK            = 'low_stock',            'Low Stock Alert'
    OUT_OF_STOCK_ALERT   = 'out_of_stock_alert',   'Product Out of Stock'
    BACK_IN_STOCK        = 'back_in_stock',        'Back in Stock'
    REORDER_POINT        = 'reorder_point',        'Reorder Point Reached'
    PO_REMINDER          = 'po_reminder',          'Purchase Order Due'
    AUDIT_COMPLETE       = 'audit_complete',       'Stock Audit Complete'
    WEEKLY_STOCK_SUMMARY = 'weekly_stock_summary', 'Weekly Stock Summary'
    # Referral
    REFERRAL_REWARD         = 'referral_reward',         'Referral Reward'


class Notification(BaseModel):
    recipient         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices, db_index=True)
    title             = models.CharField(max_length=200)
    body              = models.TextField()
    data              = models.JSONField(default=dict, blank=True)
    is_read           = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['recipient', 'is_read'],            name='notif_recipient_read_idx'),
            models.Index(fields=['recipient', 'created_at'],         name='notif_recipient_time_idx'),
            models.Index(fields=['recipient', 'notification_type'],  name='notif_recipient_type_idx'),
        ]

    def __str__(self):
        return f'[{self.notification_type}] → {self.recipient} | {self.title}'
