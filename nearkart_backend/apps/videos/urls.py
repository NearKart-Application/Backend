from django.urls import path

from .views import (
    VideoConfirmUploadView,
    VideoDeleteView,
    VideoDetailView,
    VideoFeedView,
    VideoLikeView,
    VideoUploadRequestView,
)

urlpatterns = [
    path('request-upload/',                VideoUploadRequestView.as_view(),  name='video-request-upload'),
    path('feed/',                           VideoFeedView.as_view(),            name='video-feed'),
    path('<uuid:video_id>/',               VideoDetailView.as_view(),          name='video-detail'),
    path('<uuid:video_id>/confirm-upload/', VideoConfirmUploadView.as_view(),  name='video-confirm-upload'),
    path('<uuid:video_id>/delete/',         VideoDeleteView.as_view(),          name='video-delete'),
    path('<uuid:video_id>/like/',           VideoLikeView.as_view(),            name='video-like'),
]
