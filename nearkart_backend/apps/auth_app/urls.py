from django.urls import path
from .views import (
    OTPSendView,
    OTPVerifyView,
    TokenRefreshView,
    MeView,
    AvatarUploadView,
    LocationUpdateView,
    PopularLocationsView,
    LogoutView,
    UserSearchView,
    ClientLogsView,
    SessionListView,
    AccountDeleteView,
    SocialGoogleView,
)

urlpatterns = [
    path('otp/send/',      OTPSendView.as_view(),     name='otp-send'),
    path('otp/verify/',    OTPVerifyView.as_view(),    name='otp-verify'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/',            MeView.as_view(),            name='me'),
    path('me/avatar/',     AvatarUploadView.as_view(),  name='me-avatar'),
    path('me/location/',   LocationUpdateView.as_view(), name='location-update'),
    path('me/sessions/',   SessionListView.as_view(),   name='me-sessions'),
    path('me/delete/',     AccountDeleteView.as_view(), name='account-delete'),
    path('popular-locations/', PopularLocationsView.as_view(), name='popular-locations'),
    path('logout/',        LogoutView.as_view(),        name='logout'),
    path('users/search/',  UserSearchView.as_view(),    name='user-search'),
    path('client-logs/',   ClientLogsView.as_view(),    name='client-logs'),
    path('social/google/', SocialGoogleView.as_view(),  name='social-google'),
]
