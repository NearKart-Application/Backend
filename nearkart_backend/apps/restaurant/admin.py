from django.contrib import admin
from .models import Ingredient, Recipe, RecipeIngredient, RestaurantWastage, DailyStock

admin.site.register(Ingredient)
admin.site.register(Recipe)
admin.site.register(RecipeIngredient)
admin.site.register(RestaurantWastage)
admin.site.register(DailyStock)
