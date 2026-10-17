from datetime import date, timedelta
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth, TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from rest_framework.permissions import IsAuthenticated
from core.permissions import IsVendor
from apps.stores.models import Store
from .models import Expense, ExpenseCategory, PREDEFINED_CATEGORIES
from .serializers import ExpenseSerializer, ExpenseCategorySerializer


def _vendor_store(request):
    return Store.objects.filter(owner=request.user, is_active=True).first()


class CategoryListView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _vendor_store(request)
        if not store:
            return Response({'detail': 'No active store.'}, status=404)
        cats = ExpenseCategory.objects.filter(store=store)
        return Response(ExpenseCategorySerializer(cats, many=True).data)

    def post(self, request):
        store = _vendor_store(request)
        if not store:
            return Response({'detail': 'No active store.'}, status=404)
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'detail': 'Name is required.'}, status=400)
        cat, _ = ExpenseCategory.objects.get_or_create(store=store, name=name)
        return Response(ExpenseCategorySerializer(cat).data, status=201)


class CategoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def delete(self, request, category_id):
        store = _vendor_store(request)
        try:
            cat = ExpenseCategory.objects.get(id=category_id, store=store, is_system=False)
        except ExpenseCategory.DoesNotExist:
            return Response(status=404)
        cat.delete()
        return Response(status=204)


class EnsureSystemCategoriesView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request):
        store = _vendor_store(request)
        if not store:
            return Response({'detail': 'No active store.'}, status=404)
        created = []
        for name in PREDEFINED_CATEGORIES:
            cat, is_new = ExpenseCategory.objects.get_or_create(store=store, name=name, defaults={'is_system': True})
            if is_new:
                created.append(name)
        return Response({'created': created})


class ExpenseListView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _vendor_store(request)
        if not store:
            return Response({'detail': 'No active store.'}, status=404)

        qs = Expense.objects.filter(store=store).select_related('category')

        # Filters
        category_id = request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)

        month = request.query_params.get('month')  # YYYY-MM
        if month:
            try:
                y, m = month.split('-')
                qs = qs.filter(date__year=int(y), date__month=int(m))
            except (ValueError, AttributeError):
                pass

        date_from = request.query_params.get('from')
        date_to   = request.query_params.get('to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        is_recurring = request.query_params.get('recurring')
        if is_recurring == '1':
            qs = qs.filter(is_recurring=True)

        return Response(ExpenseSerializer(qs, many=True, context={'request': request}).data)

    def post(self, request):
        store = _vendor_store(request)
        if not store:
            return Response({'detail': 'No active store.'}, status=404)

        serializer = ExpenseSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        # Validate category belongs to store
        cat = serializer.validated_data.get('category')
        if cat and cat.store != store:
            return Response({'detail': 'Invalid category.'}, status=400)

        expense = serializer.save(store=store, recorded_by=request.user)
        return Response(ExpenseSerializer(expense, context={'request': request}).data, status=201)


class ExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get(self, request, expense_id):
        store = _vendor_store(request)
        try:
            return Expense.objects.get(id=expense_id, store=store)
        except Expense.DoesNotExist:
            return None

    def get(self, request, expense_id):
        exp = self._get(request, expense_id)
        if not exp:
            return Response(status=404)
        return Response(ExpenseSerializer(exp, context={'request': request}).data)

    def patch(self, request, expense_id):
        exp = self._get(request, expense_id)
        if not exp:
            return Response(status=404)
        serializer = ExpenseSerializer(exp, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, expense_id):
        exp = self._get(request, expense_id)
        if not exp:
            return Response(status=404)
        exp.delete()
        return Response(status=204)


class ReceiptUploadView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]
    parser_classes = [MultiPartParser]

    def post(self, request, expense_id):
        store = _vendor_store(request)
        try:
            exp = Expense.objects.get(id=expense_id, store=store)
        except Expense.DoesNotExist:
            return Response(status=404)

        image = request.FILES.get('receipt')
        if not image:
            return Response({'detail': 'receipt file required.'}, status=400)

        exp.receipt_image = image
        exp.save(update_fields=['receipt_image'])
        return Response(ExpenseSerializer(exp, context={'request': request}).data)


class ExpenseSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _vendor_store(request)
        if not store:
            return Response({'detail': 'No active store.'}, status=404)

        qs = Expense.objects.filter(store=store)

        today = date.today()
        month_start = today.replace(day=1)

        today_total  = qs.filter(date=today).aggregate(t=Sum('amount'))['t'] or 0
        month_total  = qs.filter(date__gte=month_start).aggregate(t=Sum('amount'))['t'] or 0
        gst_month    = qs.filter(date__gte=month_start).aggregate(t=Sum('gst_amount'))['t'] or 0

        # Monthly breakdown for last 6 months
        six_ago = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        six_ago = six_ago.replace(month=max(1, today.month - 5)) if today.month > 5 else date(today.year - 1, today.month + 7, 1)

        monthly = (
            qs.filter(date__gte=six_ago)
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(total=Sum('amount'), gst=Sum('gst_amount'))
            .order_by('month')
        )

        # By category this month
        by_category = (
            qs.filter(date__gte=month_start)
            .values('category__name', 'category_name')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )
        category_breakdown = [
            {'category': r['category__name'] or r['category_name'] or 'Uncategorized', 'total': str(r['total'])}
            for r in by_category
        ]

        return Response({
            'today_total':        str(today_total),
            'month_total':        str(month_total),
            'month_gst':          str(gst_month),
            'category_breakdown': category_breakdown,
            'monthly_trend': [
                {'month': r['month'].strftime('%Y-%m'), 'total': str(r['total']), 'gst': str(r['gst'] or 0)}
                for r in monthly
            ],
        })


class PnLView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _vendor_store(request)
        if not store:
            return Response({'detail': 'No active store.'}, status=404)

        month = request.query_params.get('month')
        today = date.today()

        if month:
            try:
                y, m = month.split('-')
                month_start = date(int(y), int(m), 1)
            except (ValueError, AttributeError):
                month_start = today.replace(day=1)
        else:
            month_start = today.replace(day=1)

        # Next month start for upper bound
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1)

        total_expenses = Expense.objects.filter(
            store=store, date__gte=month_start, date__lt=month_end
        ).aggregate(t=Sum('amount'))['t'] or 0

        total_gst = Expense.objects.filter(
            store=store, date__gte=month_start, date__lt=month_end
        ).aggregate(t=Sum('gst_amount'))['t'] or 0

        # Revenue from invoices for the same period
        revenue = 0
        try:
            from apps.stores.models import Invoice
            revenue = Invoice.objects.filter(
                store=store,
                created_at__date__gte=month_start,
                created_at__date__lt=month_end,
            ).aggregate(t=Sum('total'))['t'] or 0
        except Exception:
            logger.exception('[PnLView] revenue query failed for store %s', store.id)

        gross_profit = float(revenue) - float(total_expenses)

        return Response({
            'month':           month_start.strftime('%Y-%m'),
            'revenue':         str(revenue),
            'total_expenses':  str(total_expenses),
            'total_gst_paid':  str(total_gst),
            'gross_profit':    str(gross_profit),
            'profit_margin':   f"{(gross_profit / float(revenue) * 100):.1f}%" if revenue else "N/A",
        })
