from django.urls import path
from .views import (
    PlanListView, WalletView, TopupView,
    SubscribeView, SubscriptionStatusView, TransactionListView,
    PaymentInitiateView, PaymentVerifyView, PaymentWebhookView,
    CouponValidateView, MyCouponsView, VendorReferralView,
    SubscriptionRefundRequestView, SubscriptionInvoiceView,
    WalletTopupInitiateView, WalletTopupVerifyView,
)

urlpatterns = [
    path('plans/',                    PlanListView.as_view(),                name='billing-plans'),
    path('wallet/',                   WalletView.as_view(),                  name='billing-wallet'),
    path('topup/',                    TopupView.as_view(),                   name='billing-topup'),
    path('subscribe/',                SubscribeView.as_view(),               name='billing-subscribe'),
    path('subscription/',             SubscriptionStatusView.as_view(),      name='billing-subscription'),
    path('subscription/refund/',      SubscriptionRefundRequestView.as_view(), name='billing-subscription-refund'),
    path('subscription/invoice/',     SubscriptionInvoiceView.as_view(),     name='billing-subscription-invoice'),
    path('transactions/',             TransactionListView.as_view(),         name='billing-transactions'),
    path('coupon/validate/',          CouponValidateView.as_view(),          name='billing-coupon-validate'),
    path('my-coupons/',               MyCouponsView.as_view(),               name='billing-my-coupons'),
    path('referral/',                 VendorReferralView.as_view(),          name='billing-referral'),
    # Razorpay plan payment flow
    path('payment/initiate/',         PaymentInitiateView.as_view(),         name='billing-payment-initiate'),
    path('payment/verify/',           PaymentVerifyView.as_view(),           name='billing-payment-verify'),
    path('payment/webhook/',          PaymentWebhookView.as_view(),          name='billing-payment-webhook'),
    # Razorpay wallet top-up flow
    path('wallet/topup/initiate/',    WalletTopupInitiateView.as_view(),     name='billing-wallet-topup-initiate'),
    path('wallet/topup/verify/',      WalletTopupVerifyView.as_view(),       name='billing-wallet-topup-verify'),
]
