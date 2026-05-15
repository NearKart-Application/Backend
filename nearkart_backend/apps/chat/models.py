"""
NearKart — Chat Models
Conversation: one per (customer, store) pair
Message: individual chat message inside a conversation
"""
from django.db import models
from django.conf import settings

from core.models import BaseModel
from apps.stores.models import Store


class Conversation(BaseModel):
    customer             = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='conversations_as_customer',
    )
    store                = models.ForeignKey(
        Store, on_delete=models.CASCADE, related_name='conversations',
    )
    last_message_at      = models.DateTimeField(null=True, blank=True, db_index=True)
    unread_count_customer = models.PositiveIntegerField(default=0)
    unread_count_vendor   = models.PositiveIntegerField(default=0)
    is_active            = models.BooleanField(default=True)

    class Meta:
        db_table        = 'conversations'
        unique_together = [('customer', 'store')]
        ordering        = ['-last_message_at']

    def __str__(self):
        return f'{self.customer.phone_number} ↔ {self.store.name}'


class Message(BaseModel):
    TYPE_TEXT        = 'text'
    TYPE_IMAGE       = 'image'
    TYPE_PRODUCT_REF = 'product_ref'
    TYPE_VIDEO_REF   = 'video_ref'

    TYPE_CHOICES = [
        (TYPE_TEXT,        'Text'),
        (TYPE_IMAGE,       'Image'),
        (TYPE_PRODUCT_REF, 'Product Reference'),
        (TYPE_VIDEO_REF,   'Video Reference'),
    ]

    conversation  = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages',
    )
    sender        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    content       = models.TextField(blank=True)
    message_type  = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_TEXT,
    )
    media_url     = models.URLField(max_length=500, blank=True)
    ref_id        = models.UUIDField(null=True, blank=True)
    is_read       = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']
        indexes  = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        return f'[{self.conversation_id}] {self.sender.phone_number}: {self.content[:40]}'
