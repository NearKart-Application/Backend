from django.urls import path
from .views import (
    OTPSendView,
    OTPVerifyView,
    TokenRefreshView,
    MeView,
    LocationUpdateView,
    LogoutView,
    UserSearchView,
    ClientLogsView,
)

urlpatterns = [
    path('otp/send/',      OTPSendView.as_view(),     name='otp-send'),
    path('otp/verify/',    OTPVerifyView.as_view(),    name='otp-verify'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/',            MeView.as_view(),            name='me'),
    path('me/location/',   LocationUpdateView.as_view(), name='location-update'),
    path('logout/',        LogoutView.as_view(),        name='logout'),
    path('users/search/',  UserSearchView.as_view(),    name='user-search'),
    path('client-logs/',   ClientLogsView.as_view(),    name='client-logs'),
]
