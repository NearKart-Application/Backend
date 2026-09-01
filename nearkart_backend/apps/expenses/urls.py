from django.urls import path
from .views import (
    CategoryListView, CategoryDetailView, EnsureSystemCategoriesView,
    ExpenseListView, ExpenseDetailView, ReceiptUploadView,
    ExpenseSummaryView, PnLView,
)

urlpatterns = [
    path('categories/',                          CategoryListView.as_view(),           name='expense-categories'),
    path('categories/init/',                     EnsureSystemCategoriesView.as_view(), name='expense-categories-init'),
    path('categories/<uuid:category_id>/',       CategoryDetailView.as_view(),         name='expense-category-detail'),
    path('',                                     ExpenseListView.as_view(),            name='expense-list'),
    path('<uuid:expense_id>/',                   ExpenseDetailView.as_view(),          name='expense-detail'),
    path('<uuid:expense_id>/receipt/',           ReceiptUploadView.as_view(),          name='expense-receipt'),
    path('summary/',                             ExpenseSummaryView.as_view(),         name='expense-summary'),
    path('pnl/',                                 PnLView.as_view(),                    name='expense-pnl'),
]
