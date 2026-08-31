from django.urls import path
from .views import WalletWithdrawalRequestView

urlpatterns = [
    path('requests/', WalletWithdrawalRequestView.as_view(), name='wallet-withdrawal-requests'),
]
