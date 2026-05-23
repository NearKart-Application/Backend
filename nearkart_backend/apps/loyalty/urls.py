from django.urls import path
from .views import LoyaltyBalanceView, LoyaltyHistoryView, ApplyReferralView, RedeemPointsView

urlpatterns = [
    path('',                  LoyaltyBalanceView.as_view(),  name='loyalty-balance'),
    path('history/',          LoyaltyHistoryView.as_view(),  name='loyalty-history'),
    path('apply-referral/',   ApplyReferralView.as_view(),   name='loyalty-apply-referral'),
    path('redeem/',           RedeemPointsView.as_view(),    name='loyalty-redeem'),
]
