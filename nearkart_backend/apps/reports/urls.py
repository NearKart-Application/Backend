from django.urls import path
from .views import (
    DayBookView, PnLView, CashFlowView, TopProductsView,
    ABCAnalysisView, GrossMarginView, GSTReportView, ExportCSVView,
)

urlpatterns = [
    path('day-book/',    DayBookView.as_view(),    name='report-day-book'),
    path('pnl/',         PnLView.as_view(),         name='report-pnl'),
    path('cash-flow/',   CashFlowView.as_view(),   name='report-cash-flow'),
    path('top-products/', TopProductsView.as_view(), name='report-top-products'),
    path('abc/',         ABCAnalysisView.as_view(), name='report-abc'),
    path('gross-margin/', GrossMarginView.as_view(), name='report-gross-margin'),
    path('gst/',         GSTReportView.as_view(),   name='report-gst'),
    path('export/',      ExportCSVView.as_view(),   name='report-export'),
]
