"""Nearspot — Restaurant Inventory Views (#133–#138)"""
import logging
from datetime import date

from rest_framework.views import APIView
from rest_framework.response import Response

from core.permissions import IsVendor
from .models import Ingredient, Recipe, RecipeIngredient, RestaurantWastage, DailyStock
from .serializers import (
    IngredientSerializer, RecipeSerializer, RecipeIngredientSerializer,
    RestaurantWastageSerializer, DailyStockSerializer,
)

logger = logging.getLogger(__name__)


def _vendor_store(request):
    return request.user.store


# ── Ingredients (#133) ────────────────────────────────────────────────────────

class IngredientListView(APIView):
    permission_classes = [IsVendor]

    def get(self, request):
        store = _vendor_store(request)
        qs = Ingredient.objects.filter(store=store)
        low = request.query_params.get('low_stock')
        if low == 'true':
            # Filter ingredients where current_stock <= reorder_level
            from django.db.models import F
            qs = qs.filter(current_stock__lte=F('reorder_level'))
        return Response(IngredientSerializer(qs, many=True).data)

    def post(self, request):
        store = _vendor_store(request)
        ser = IngredientSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        ingredient = ser.save(store=store)
        return Response(IngredientSerializer(ingredient).data, status=201)


class IngredientDetailView(APIView):
    permission_classes = [IsVendor]

    def _get(self, request, ingredient_id):
        store = _vendor_store(request)
        try:
            return Ingredient.objects.get(id=ingredient_id, store=store)
        except Ingredient.DoesNotExist:
            return None

    def get(self, request, ingredient_id):
        obj = self._get(request, ingredient_id)
        if not obj:
            return Response({'error': 'Not found.'}, status=404)
        return Response(IngredientSerializer(obj).data)

    def patch(self, request, ingredient_id):
        obj = self._get(request, ingredient_id)
        if not obj:
            return Response({'error': 'Not found.'}, status=404)
        ser = IngredientSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        ser.save()
        return Response(IngredientSerializer(obj).data)

    def delete(self, request, ingredient_id):
        obj = self._get(request, ingredient_id)
        if not obj:
            return Response({'error': 'Not found.'}, status=404)
        obj.delete()
        return Response(status=204)


# ── Recipes / BOM (#134) ──────────────────────────────────────────────────────

class RecipeListView(APIView):
    permission_classes = [IsVendor]

    def get(self, request):
        store = _vendor_store(request)
        qs = Recipe.objects.filter(store=store).prefetch_related('ingredients__ingredient')
        return Response(RecipeSerializer(qs, many=True).data)

    def post(self, request):
        store = _vendor_store(request)
        ser = RecipeSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        recipe = ser.save(store=store)
        return Response(RecipeSerializer(recipe).data, status=201)


class RecipeDetailView(APIView):
    permission_classes = [IsVendor]

    def _get(self, request, recipe_id):
        store = _vendor_store(request)
        try:
            return Recipe.objects.prefetch_related('ingredients__ingredient').get(id=recipe_id, store=store)
        except Recipe.DoesNotExist:
            return None

    def get(self, request, recipe_id):
        obj = self._get(request, recipe_id)
        if not obj:
            return Response({'error': 'Not found.'}, status=404)
        return Response(RecipeSerializer(obj).data)

    def patch(self, request, recipe_id):
        obj = self._get(request, recipe_id)
        if not obj:
            return Response({'error': 'Not found.'}, status=404)
        ser = RecipeSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        ser.save()
        return Response(RecipeSerializer(obj).data)

    def delete(self, request, recipe_id):
        obj = self._get(request, recipe_id)
        if not obj:
            return Response({'error': 'Not found.'}, status=404)
        obj.delete()
        return Response(status=204)


class RecipeIngredientView(APIView):
    """Add / remove ingredients from a recipe."""
    permission_classes = [IsVendor]

    def post(self, request, recipe_id):
        store = _vendor_store(request)
        try:
            recipe = Recipe.objects.get(id=recipe_id, store=store)
        except Recipe.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)

        ser = RecipeIngredientSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        ingredient = ser.validated_data['ingredient']
        if ingredient.store_id != store.id:
            return Response({'error': 'Ingredient not in your store.'}, status=403)

        ri, _ = RecipeIngredient.objects.update_or_create(
            recipe=recipe,
            ingredient=ingredient,
            defaults={'quantity_per_serving': ser.validated_data['quantity_per_serving']},
        )
        return Response(RecipeIngredientSerializer(ri).data, status=201)

    def delete(self, request, recipe_id, ri_id):
        store = _vendor_store(request)
        try:
            ri = RecipeIngredient.objects.get(id=ri_id, recipe__store=store, recipe_id=recipe_id)
        except RecipeIngredient.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)
        ri.delete()
        return Response(status=204)


# ── Auto Deduction per Sale (#135) ────────────────────────────────────────────

class RecipeDeductView(APIView):
    """
    POST /restaurant/recipes/<recipe_id>/deduct/?servings=N
    Deducts ingredient stock for N servings of this recipe.
    """
    permission_classes = [IsVendor]

    def post(self, request, recipe_id):
        store = _vendor_store(request)
        try:
            recipe = Recipe.objects.prefetch_related('ingredients__ingredient').get(id=recipe_id, store=store)
        except Recipe.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)

        servings = int(request.data.get('servings', 1))
        if servings < 1:
            return Response({'error': 'servings must be ≥ 1.'}, status=400)

        deductions = []
        for ri in recipe.ingredients.all():
            qty = ri.quantity_per_serving * servings
            ing = ri.ingredient
            ing.current_stock = max(ing.current_stock - qty, 0)
            ing.save(update_fields=['current_stock'])
            deductions.append({
                'ingredient': ing.name,
                'deducted':   str(qty),
                'remaining':  str(ing.current_stock),
                'unit':       ing.unit,
            })

        return Response({'recipe': recipe.name, 'servings': servings, 'deductions': deductions})


# ── Wastage (#137) ────────────────────────────────────────────────────────────

class RestaurantWastageListView(APIView):
    permission_classes = [IsVendor]

    def get(self, request):
        store = _vendor_store(request)
        qs = RestaurantWastage.objects.filter(
            ingredient__store=store,
        ).select_related('ingredient')
        date_str = request.query_params.get('date')
        if date_str:
            qs = qs.filter(date=date_str)
        return Response(RestaurantWastageSerializer(qs, many=True).data)

    def post(self, request):
        store = _vendor_store(request)
        ser = RestaurantWastageSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        ingredient = ser.validated_data['ingredient']
        if ingredient.store_id != store.id:
            return Response({'error': 'Ingredient not in your store.'}, status=403)

        record = ser.save(recorded_by=request.user)
        return Response(RestaurantWastageSerializer(record).data, status=201)


# ── Daily Stock (#136, #138) ──────────────────────────────────────────────────

class DailyStockListView(APIView):
    permission_classes = [IsVendor]

    def get(self, request):
        store = _vendor_store(request)
        qs = DailyStock.objects.filter(ingredient__store=store).select_related('ingredient')
        date_str = request.query_params.get('date')
        if date_str:
            qs = qs.filter(date=date_str)
        return Response(DailyStockSerializer(qs, many=True).data)

    def post(self, request):
        """Create opening stock record for today."""
        store = _vendor_store(request)
        ser = DailyStockSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        ingredient = ser.validated_data['ingredient']
        if ingredient.store_id != store.id:
            return Response({'error': 'Ingredient not in your store.'}, status=403)

        ds, created = DailyStock.objects.get_or_create(
            ingredient=ingredient,
            date=ser.validated_data['date'],
            defaults={
                'opening_stock': ser.validated_data['opening_stock'],
                'received':      ser.validated_data.get('received', 0),
                'notes':         ser.validated_data.get('notes', ''),
                'recorded_by':   request.user,
            },
        )
        if not created:
            return Response({'error': 'Daily stock entry for this ingredient/date already exists.'}, status=409)
        return Response(DailyStockSerializer(ds).data, status=201)


class DailyStockDetailView(APIView):
    permission_classes = [IsVendor]

    def _get(self, request, ds_id):
        store = _vendor_store(request)
        try:
            return DailyStock.objects.select_related('ingredient').get(id=ds_id, ingredient__store=store)
        except DailyStock.DoesNotExist:
            return None

    def patch(self, request, ds_id):
        """Update closing stock (end-of-day)."""
        ds = self._get(request, ds_id)
        if not ds:
            return Response({'error': 'Not found.'}, status=404)
        ser = DailyStockSerializer(ds, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        ser.save()
        return Response(DailyStockSerializer(ds).data)


class DailyConsumptionSummaryView(APIView):
    """GET /restaurant/daily-consumption/?date=YYYY-MM-DD — summary across all ingredients."""
    permission_classes = [IsVendor]

    def get(self, request):
        store = _vendor_store(request)
        date_str = request.query_params.get('date', str(date.today()))
        qs = DailyStock.objects.filter(
            ingredient__store=store,
            date=date_str,
        ).select_related('ingredient')

        items = []
        for ds in qs:
            items.append({
                'ingredient':    ds.ingredient.name,
                'unit':          ds.ingredient.unit,
                'opening_stock': str(ds.opening_stock),
                'received':      str(ds.received),
                'closing_stock': str(ds.closing_stock) if ds.closing_stock is not None else None,
                'consumed':      str(ds.consumed) if ds.consumed is not None else None,
                'cost_per_unit': str(ds.ingredient.cost_per_unit),
                'total_cost':    str(float(ds.consumed or 0) * float(ds.ingredient.cost_per_unit)) if ds.consumed else '0',
            })

        total_cost = sum(float(i['total_cost']) for i in items)
        return Response({'date': date_str, 'total_consumption_cost': f'{total_cost:.2f}', 'items': items})
