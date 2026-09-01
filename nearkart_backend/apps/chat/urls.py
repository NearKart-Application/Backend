from django.urls import path

from .views import (
    ChatMediaUploadView,
    ConversationListView,
    ConversationStartView,
    MarkReadView,
    MessageListView,
)

urlpatterns = [
    path('',                                  ConversationListView.as_view(),  name='conversation-list'),
    path('start/',                            ConversationStartView.as_view(), name='conversation-start'),
    path('<uuid:conversation_id>/messages/',  MessageListView.as_view(),       name='conversation-messages'),
    path('<uuid:conversation_id>/upload/',    ChatMediaUploadView.as_view(),   name='conversation-upload'),
    path('<uuid:conversation_id>/read/',      MarkReadView.as_view(),          name='conversation-mark-read'),
]
