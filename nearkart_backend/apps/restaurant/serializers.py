"""Nearspot — Restaurant Serializers"""
from rest_framework import serializers
from .models import Ingredient, Recipe, RecipeIngredient, RestaurantWastage, DailyStock


class IngredientSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Ingredient
        fields = [
            'id', 'store', 'name', 'unit', 'current_stock',
            'reorder_level', 'cost_per_unit', 'notes', 'is_low_stock', 'created_at',
        ]
        read_only_fields = ['id', 'store', 'created_at']


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    unit            = serializers.CharField(source='ingredient.unit', read_only=True)

    class Meta:
        model  = RecipeIngredient
        fields = ['id', 'ingredient', 'ingredient_name', 'unit', 'quantity_per_serving']
        read_only_fields = ['id']


class RecipeSerializer(serializers.ModelSerializer):
    ingredients  = RecipeIngredientSerializer(many=True, read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True, default='')

    class Meta:
        model  = Recipe
        fields = ['id', 'store', 'product', 'product_name', 'name', 'serves', 'notes', 'ingredients', 'created_at']
        read_only_fields = ['id', 'store', 'created_at']


class RestaurantWastageSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    unit            = serializers.CharField(source='ingredient.unit', read_only=True)

    class Meta:
        model  = RestaurantWastage
        fields = ['id', 'ingredient', 'ingredient_name', 'unit', 'quantity', 'reason', 'notes', 'date', 'created_at']
        read_only_fields = ['id', 'created_at']


class DailyStockSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    unit            = serializers.CharField(source='ingredient.unit', read_only=True)
    consumed        = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)

    class Meta:
        model  = DailyStock
        fields = [
            'id', 'ingredient', 'ingredient_name', 'unit',
            'date', 'opening_stock', 'closing_stock', 'received', 'consumed', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
