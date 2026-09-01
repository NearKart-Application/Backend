"""Nearspot — Restaurant Inventory Models (#133–#138)"""
from django.conf import settings
from django.db import models
from django.db.models import Sum
from core.models import BaseModel


class IngredientUnit(models.TextChoices):
    KG     = 'kg',    'Kilogram (kg)'
    GRAM   = 'g',     'Gram (g)'
    LITRE  = 'l',     'Litre (L)'
    ML     = 'ml',    'Millilitre (mL)'
    PIECE  = 'piece', 'Piece / Unit'
    DOZEN  = 'dozen', 'Dozen'


class Ingredient(BaseModel):
    """Raw material / ingredient tracked for a restaurant store."""
    store         = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='ingredients')
    name          = models.CharField(max_length=200)
    unit          = models.CharField(max_length=10, choices=IngredientUnit.choices, default=IngredientUnit.PIECE)
    current_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes         = models.TextField(blank=True)

    class Meta:
        db_table = 'rest_ingredients'
        ordering = ['name']
        unique_together = [('store', 'name')]

    def __str__(self):
        return f'{self.name} ({self.unit}) — {self.store.name}'

    @property
    def is_low_stock(self):
        return self.current_stock <= self.reorder_level


class Recipe(BaseModel):
    """
    Bill of Materials linking a menu Product to its ingredient quantities.
    One product can have one recipe; one recipe has many RecipeIngredient rows.
    """
    store   = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='recipes')
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE, related_name='recipe', null=True, blank=True)
    name    = models.CharField(max_length=200)
    serves  = models.PositiveIntegerField(default=1, help_text='Number of servings this recipe makes')
    notes   = models.TextField(blank=True)

    class Meta:
        db_table = 'rest_recipes'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.store.name})'


class RecipeIngredient(BaseModel):
    """One ingredient line in a recipe."""
    recipe                = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    ingredient            = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='used_in_recipes')
    quantity_per_serving  = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        db_table = 'rest_recipe_ingredients'
        unique_together = [('recipe', 'ingredient')]

    def __str__(self):
        return f'{self.ingredient.name} × {self.quantity_per_serving} in {self.recipe.name}'


class WastageReason(models.TextChoices):
    SPOILED       = 'spoiled',        'Spoiled / Expired'
    PREP_WASTE    = 'prep_waste',     'Prep Waste (peeling/cutting)'
    OVERPRODUCED  = 'overproduced',   'Overproduction'
    SPILLAGE      = 'spillage',       'Spillage'
    OTHER         = 'other',          'Other'


class RestaurantWastage(BaseModel):
    """Records ingredient wastage for a restaurant."""
    ingredient  = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='wastage_records')
    quantity    = models.DecimalField(max_digits=12, decimal_places=3)
    reason      = models.CharField(max_length=20, choices=WastageReason.choices, default=WastageReason.OTHER)
    notes       = models.TextField(blank=True)
    date        = models.DateField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'rest_wastage_records'
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Deduct from current_stock
        ing = self.ingredient
        ing.current_stock = max(ing.current_stock - self.quantity, 0)
        ing.save(update_fields=['current_stock'])


class DailyStock(BaseModel):
    """
    Opening/closing stock snapshot per ingredient per day.
    Used for daily consumption tracking (#136, #138).
    """
    ingredient    = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='daily_stocks')
    date          = models.DateField()
    opening_stock = models.DecimalField(max_digits=12, decimal_places=3)
    closing_stock = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    received      = models.DecimalField(max_digits=12, decimal_places=3, default=0, help_text='Deliveries received this day')
    notes         = models.TextField(blank=True)
    recorded_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'rest_daily_stocks'
        ordering = ['-date']
        unique_together = [('ingredient', 'date')]

    @property
    def consumed(self):
        if self.closing_stock is None:
            return None
        return max(self.opening_stock + self.received - self.closing_stock, 0)
