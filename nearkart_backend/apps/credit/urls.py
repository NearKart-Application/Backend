from django.urls import path
from .views import (
    CreditAccountListView,
    CreditAccountDetailView,
    CreditTransactionView,
    CreditAgingReportView,
    CreditReminderView,
    CustomerDuesView,
    CreditStatementView,
)

urlpatterns = [
    path('customers/',                                     CreditAccountListView.as_view(),   name='credit-accounts'),
    path('customers/<uuid:account_id>/',                   CreditAccountDetailView.as_view(), name='credit-account-detail'),
    path('customers/<uuid:account_id>/transactions/',      CreditTransactionView.as_view(),   name='credit-transactions'),
    path('customers/<uuid:account_id>/remind/',            CreditReminderView.as_view(),      name='credit-remind'),
    path('customers/<uuid:account_id>/statement/',         CreditStatementView.as_view(),     name='credit-statement'),
    path('aging/',                                         CreditAgingReportView.as_view(),   name='credit-aging'),
    path('my-dues/',                                       CustomerDuesView.as_view(),        name='credit-my-dues'),
]
