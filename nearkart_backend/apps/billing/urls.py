from django.urls import path
from .views import (
    PlanListView, WalletView, TopupView,
    SubscribeView, SubscriptionStatusView, TransactionListView,
    PaymentInitiateView, PaymentVerifyView, PaymentWebhookView,
)

urlpatterns = [
    path('plans/',                PlanListView.as_view(),          name='billing-plans'),
    path('wallet/',               WalletView.as_view(),             name='billing-wallet'),
    path('topup/',                TopupView.as_view(),              name='billing-topup'),
    path('subscribe/',            SubscribeView.as_view(),          name='billing-subscribe'),
    path('subscription/',         SubscriptionStatusView.as_view(), name='billing-subscription'),
    path('transactions/',         TransactionListView.as_view(),    name='billing-transactions'),
    # Razorpay payment flow
    path('payment/initiate/',     PaymentInitiateView.as_view(),    name='billing-payment-initiate'),
    path('payment/verify/',       PaymentVerifyView.as_view(),      name='billing-payment-verify'),
    path('payment/webhook/',      PaymentWebhookView.as_view(),     name='billing-payment-webhook'),
]
