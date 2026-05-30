from django.urls import path

from .views import (
    VideoConfirmUploadView,
    VideoDeleteView,
    VideoDetailView,
    VideoDownloadView,
    VideoFeedView,
    VideoFollowingFeedView,
    VideoTrendingFeedView,
    VideoLikeView,
    VideoSaveView,
    VideoTagsView,
    VideoTagDeleteView,
    MyVideosView,
    VideoUpdateView,
    VideoUploadRequestView,
)

urlpatterns = [
    path('request-upload/',                          VideoUploadRequestView.as_view(),  name='video-request-upload'),
    path('my-videos/',                               MyVideosView.as_view(),             name='video-my-videos'),
    path('feed/',                                    VideoFeedView.as_view(),            name='video-feed'),
    path('feed/following/',                          VideoFollowingFeedView.as_view(),   name='video-feed-following'),
    path('feed/trending/',                           VideoTrendingFeedView.as_view(),    name='video-feed-trending'),
    path('<uuid:video_id>/',                         VideoDetailView.as_view(),          name='video-detail'),
    path('<uuid:video_id>/confirm-upload/',          VideoConfirmUploadView.as_view(),   name='video-confirm-upload'),
    path('<uuid:video_id>/update/',                  VideoUpdateView.as_view(),          name='video-update'),
    path('<uuid:video_id>/delete/',                  VideoDeleteView.as_view(),          name='video-delete'),
    path('<uuid:video_id>/like/',                    VideoLikeView.as_view(),            name='video-like'),
    path('<uuid:video_id>/save/',                    VideoSaveView.as_view(),            name='video-save'),
    path('<uuid:video_id>/download/',                VideoDownloadView.as_view(),        name='video-download'),
    path('<uuid:video_id>/tags/',                    VideoTagsView.as_view(),            name='video-tags'),
    path('<uuid:video_id>/tags/<uuid:tag_id>/',      VideoTagDeleteView.as_view(),       name='video-tag-delete'),
]
