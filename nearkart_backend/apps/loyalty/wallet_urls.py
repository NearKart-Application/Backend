from django.urls import path
from .views import WalletWithdrawalRequestView, WalletTopupInitiateView, WalletTopupVerifyView

urlpatterns = [
    path('requests/', WalletWithdrawalRequestView.as_view(), name='wallet-withdrawal-requests'),
    path('topup/initiate/', WalletTopupInitiateView.as_view(), name='wallet-topup-initiate'),
    path('topup/verify/', WalletTopupVerifyView.as_view(), name='wallet-topup-verify'),
]
