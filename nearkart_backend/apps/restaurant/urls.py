from django.urls import path
from .views import (
    IngredientListView, IngredientDetailView,
    RecipeListView, RecipeDetailView, RecipeIngredientView, RecipeDeductView,
    RestaurantWastageListView,
    DailyStockListView, DailyStockDetailView, DailyConsumptionSummaryView,
)

app_name = 'restaurant'

urlpatterns = [
    # Ingredients
    path('ingredients/',                          IngredientListView.as_view(),   name='ingredient-list'),
    path('ingredients/<uuid:ingredient_id>/',     IngredientDetailView.as_view(), name='ingredient-detail'),

    # Recipes / BOM
    path('recipes/',                              RecipeListView.as_view(),          name='recipe-list'),
    path('recipes/<uuid:recipe_id>/',             RecipeDetailView.as_view(),         name='recipe-detail'),
    path('recipes/<uuid:recipe_id>/ingredients/', RecipeIngredientView.as_view(),     name='recipe-ingredients'),
    path('recipes/<uuid:recipe_id>/ingredients/<uuid:ri_id>/', RecipeIngredientView.as_view(), name='recipe-ingredient-delete'),
    path('recipes/<uuid:recipe_id>/deduct/',      RecipeDeductView.as_view(),         name='recipe-deduct'),

    # Wastage
    path('wastage/',                              RestaurantWastageListView.as_view(), name='wastage-list'),

    # Daily stock
    path('daily-stock/',                          DailyStockListView.as_view(),        name='daily-stock-list'),
    path('daily-stock/<uuid:ds_id>/',             DailyStockDetailView.as_view(),      name='daily-stock-detail'),
    path('daily-consumption/',                    DailyConsumptionSummaryView.as_view(), name='daily-consumption'),
]
