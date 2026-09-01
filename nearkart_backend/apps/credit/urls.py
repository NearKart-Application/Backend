from django.urls import path
from .views import (
    CreditAccountListView,
    CreditAccountDetailView,
    CreditTransactionView,
    CreditAgingReportView,
)

urlpatterns = [
    path('customers/',                           CreditAccountListView.as_view(),   name='credit-accounts'),
    path('customers/<uuid:account_id>/',         CreditAccountDetailView.as_view(), name='credit-account-detail'),
    path('customers/<uuid:account_id>/transactions/', CreditTransactionView.as_view(), name='credit-transactions'),
    path('aging/',                               CreditAgingReportView.as_view(),   name='credit-aging'),
]
