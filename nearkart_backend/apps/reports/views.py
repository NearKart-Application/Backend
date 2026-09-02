"""
Financial Reports — Area 19
#168 Day Book, #169 P&L, #170 Cash Flow, #171 Top Products,
#172 By Category, #173 By Staff (stub), #174 Stock Turnover,
#175 ABC Analysis, #176 Gross Margin, #177 Net Profit,
#178 GST Report, #179 CSV Export
"""
import csv
import io
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated
from core.permissions import IsVendor
from apps.stores.models import Store, Invoice
from apps.products.models import ProductVariant


# ── helpers ──────────────────────────────────────────────────────────────────

def _store(request):
    return Store.objects.filter(owner=request.user, is_active=True).first()


def _month_range(month_str):
    """Return (start_date, end_date exclusive) for a 'YYYY-MM' string."""
    y, m = int(month_str[:4]), int(month_str[5:7])
    start = date(y, m, 1)
    if m == 12:
        end = date(y + 1, 1, 1)
    else:
        end = date(y, m + 1, 1)
    return start, end


def _expense_total(store, start, end):
    """Total expenses (amount + gst) in date range."""
    try:
        from apps.expenses.models import Expense
        row = Expense.objects.filter(
            store=store, date__gte=start, date__lt=end, is_recurring=False
        ).aggregate(
            amt=Sum('amount'), gst=Sum('gst_amount')
        )
        return float(row['amt'] or 0) + float(row['gst'] or 0)
    except Exception:
        return 0.0


def _gst_amount(invoice):
    """Compute GST amount for a single invoice."""
    rate = float(invoice.gst_rate or 0)
    if rate == 0:
        return 0.0
    total = float(invoice.total)
    taxable = total / (1 + rate / 100)
    return total - taxable


# ── Day Book ──────────────────────────────────────────────────────────────────

class DayBookView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _store(request)
        if not store:
            return Response({'detail': 'No store.'}, status=404)

        target_date = request.query_params.get('date', str(date.today()))
        try:
            d = date.fromisoformat(target_date)
        except ValueError:
            return Response({'detail': 'Invalid date.'}, status=400)

        invoices = Invoice.objects.filter(store=store, created_at__date=d)
        total_sales  = float(invoices.aggregate(t=Sum('total'))['t'] or 0)
        invoice_count = invoices.count()

        # Item-level breakdown
        items_sold = defaultdict(lambda: {'qty': 0, 'revenue': 0.0})
        for inv in invoices:
            for it in (inv.items or []):
                name = it.get('name', 'Unknown')
                items_sold[name]['qty'] += int(it.get('qty', 1))
                items_sold[name]['revenue'] += float(it.get('price', 0)) * int(it.get('qty', 1))

        top_items = sorted(items_sold.items(), key=lambda x: -x[1]['revenue'])[:10]

        return Response({
            'date':          str(d),
            'invoice_count': invoice_count,
            'total_sales':   str(round(total_sales, 2)),
            'total_gst':     str(round(sum(_gst_amount(inv) for inv in invoices), 2)),
            'top_items': [
                {'name': k, 'qty': v['qty'], 'revenue': str(round(v['revenue'], 2))}
                for k, v in top_items
            ],
        })


# ── P&L (Monthly) ────────────────────────────────────────────────────────────

class PnLView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _store(request)
        if not store:
            return Response({'detail': 'No store.'}, status=404)

        month = request.query_params.get('month', str(date.today())[:7])
        start, end = _month_range(month)

        invoices = Invoice.objects.filter(store=store, created_at__date__gte=start, created_at__date__lt=end)
        revenue = float(invoices.aggregate(t=Sum('total'))['t'] or 0)

        # COGS: look up cost_price for each sold variant
        cogs = 0.0
        variant_ids = []
        sales_qty = defaultdict(int)
        for inv in invoices:
            for it in (inv.items or []):
                vid = it.get('variant_id')
                if vid:
                    variant_ids.append(vid)
                    sales_qty[vid] += int(it.get('qty', 1))

        for v in ProductVariant.objects.filter(id__in=set(variant_ids)):
            if v.cost_price:
                cogs += float(v.cost_price) * sales_qty[str(v.id)]

        gross_profit = revenue - cogs
        total_expenses = _expense_total(store, start, end)
        net_profit = gross_profit - total_expenses
        gross_margin = (gross_profit / revenue * 100) if revenue else 0
        net_margin   = (net_profit   / revenue * 100) if revenue else 0

        return Response({
            'month':           month,
            'revenue':         str(round(revenue, 2)),
            'cogs':            str(round(cogs, 2)),
            'gross_profit':    str(round(gross_profit, 2)),
            'gross_margin':    f"{gross_margin:.1f}%",
            'total_expenses':  str(round(total_expenses, 2)),
            'net_profit':      str(round(net_profit, 2)),
            'net_margin':      f"{net_margin:.1f}%",
        })


# ── Cash Flow ─────────────────────────────────────────────────────────────────

class CashFlowView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _store(request)
        if not store:
            return Response({'detail': 'No store.'}, status=404)

        month = request.query_params.get('month', str(date.today())[:7])
        start, end = _month_range(month)

        daily_sales = (
            Invoice.objects.filter(store=store, created_at__date__gte=start, created_at__date__lt=end)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(inflow=Sum('total'), count=Count('id'))
            .order_by('day')
        )

        # Daily expenses
        daily_expenses = {}
        try:
            from apps.expenses.models import Expense
            for row in (
                Expense.objects.filter(store=store, date__gte=start, date__lt=end)
                .values('date')
                .annotate(outflow=Sum('amount') + Sum('gst_amount'))
            ):
                daily_expenses[str(row['date'])] = float(row['outflow'] or 0)
        except Exception:
            pass

        rows = []
        running = 0.0
        for r in daily_sales:
            inflow  = float(r['inflow'] or 0)
            outflow = daily_expenses.get(str(r['day']), 0.0)
            net     = inflow - outflow
            running += net
            rows.append({
                'date':    str(r['day']),
                'inflow':  str(round(inflow, 2)),
                'outflow': str(round(outflow, 2)),
                'net':     str(round(net, 2)),
                'balance': str(round(running, 2)),
            })

        return Response({'month': month, 'rows': rows})


# ── Top Products ──────────────────────────────────────────────────────────────

class TopProductsView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _store(request)
        if not store:
            return Response({'detail': 'No store.'}, status=404)

        month = request.query_params.get('month', str(date.today())[:7])
        limit = int(request.query_params.get('limit', 10))
        start, end = _month_range(month)

        agg = defaultdict(lambda: {'qty': 0, 'revenue': 0.0})
        for inv in Invoice.objects.filter(store=store, created_at__date__gte=start, created_at__date__lt=end):
            for it in (inv.items or []):
                name = it.get('name', 'Unknown')
                agg[name]['qty']     += int(it.get('qty', 1))
                agg[name]['revenue'] += float(it.get('price', 0)) * int(it.get('qty', 1))

        ranked = sorted(agg.items(), key=lambda x: -x[1]['revenue'])[:limit]
        total_rev = sum(v['revenue'] for _, v in ranked) or 1

        return Response({
            'month': month,
            'products': [
                {
                    'name':    k,
                    'qty':     v['qty'],
                    'revenue': str(round(v['revenue'], 2)),
                    'share':   f"{v['revenue'] / total_rev * 100:.1f}%",
                }
                for k, v in ranked
            ],
        })


# ── ABC Analysis ──────────────────────────────────────────────────────────────

class ABCAnalysisView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _store(request)
        if not store:
            return Response({'detail': 'No store.'}, status=404)

        month = request.query_params.get('month', str(date.today())[:7])
        start, end = _month_range(month)

        agg = defaultdict(lambda: {'qty': 0, 'revenue': 0.0})
        for inv in Invoice.objects.filter(store=store, created_at__date__gte=start, created_at__date__lt=end):
            for it in (inv.items or []):
                name = it.get('name', 'Unknown')
                agg[name]['qty']     += int(it.get('qty', 1))
                agg[name]['revenue'] += float(it.get('price', 0)) * int(it.get('qty', 1))

        ranked = sorted(agg.items(), key=lambda x: -x[1]['revenue'])
        total = sum(v['revenue'] for _, v in ranked) or 1

        result = []
        cumulative = 0.0
        for name, v in ranked:
            cumulative += v['revenue']
            pct = cumulative / total * 100
            tier = 'A' if pct <= 70 else ('B' if pct <= 90 else 'C')
            result.append({
                'name':       name,
                'revenue':    str(round(v['revenue'], 2)),
                'qty':        v['qty'],
                'cumulative': f"{cumulative / total * 100:.1f}%",
                'tier':       tier,
            })

        return Response({'month': month, 'products': result})


# ── Gross Margin per Product ──────────────────────────────────────────────────

class GrossMarginView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _store(request)
        if not store:
            return Response({'detail': 'No store.'}, status=404)

        month = request.query_params.get('month', str(date.today())[:7])
        start, end = _month_range(month)

        # Build sales map keyed by variant_id
        variant_sales = defaultdict(lambda: {'name': '', 'qty': 0, 'revenue': 0.0})
        for inv in Invoice.objects.filter(store=store, created_at__date__gte=start, created_at__date__lt=end):
            for it in (inv.items or []):
                vid = it.get('variant_id')
                if vid:
                    variant_sales[vid]['name']    = it.get('name', '')
                    variant_sales[vid]['qty']     += int(it.get('qty', 1))
                    variant_sales[vid]['revenue'] += float(it.get('price', 0)) * int(it.get('qty', 1))

        # Join with cost_price
        variants = {str(v.id): v for v in ProductVariant.objects.filter(id__in=set(variant_sales.keys()))}
        result = []
        for vid, s in variant_sales.items():
            v = variants.get(vid)
            cost_price = float(v.cost_price) if v and v.cost_price else None
            cogs = (cost_price * s['qty']) if cost_price is not None else None
            gross = (s['revenue'] - cogs) if cogs is not None else None
            margin = (gross / s['revenue'] * 100) if (gross is not None and s['revenue']) else None
            result.append({
                'name':        s['name'],
                'qty':         s['qty'],
                'revenue':     str(round(s['revenue'], 2)),
                'cogs':        str(round(cogs, 2)) if cogs is not None else None,
                'gross_profit': str(round(gross, 2)) if gross is not None else None,
                'margin':       f"{margin:.1f}%" if margin is not None else 'N/A',
            })

        result.sort(key=lambda x: -float(x['revenue']))
        return Response({'month': month, 'products': result})


# ── GST Report ────────────────────────────────────────────────────────────────

class GSTReportView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _store(request)
        if not store:
            return Response({'detail': 'No store.'}, status=404)

        month = request.query_params.get('month', str(date.today())[:7])
        start, end = _month_range(month)

        invoices = Invoice.objects.filter(store=store, created_at__date__gte=start, created_at__date__lt=end)

        rows = []
        totals = {'taxable': 0.0, 'gst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'total': 0.0}
        for inv in invoices:
            rate = float(inv.gst_rate or 0)
            total = float(inv.total)
            if rate > 0:
                taxable = round(total / (1 + rate / 100), 2)
                gst_amt = round(total - taxable, 2)
            else:
                taxable = total
                gst_amt = 0.0
            cgst = round(gst_amt / 2, 2)
            sgst = round(gst_amt / 2, 2)

            rows.append({
                'invoice_id':    str(inv.id)[:8],
                'date':          str(inv.created_at.date()),
                'customer':      inv.customer_name,
                'gstin':         inv.gstin,
                'gst_rate':      f"{rate}%",
                'taxable':       str(taxable),
                'cgst':          str(cgst),
                'sgst':          str(sgst),
                'total_gst':     str(gst_amt),
                'invoice_total': str(total),
            })
            totals['taxable'] += taxable
            totals['gst']     += gst_amt
            totals['cgst']    += cgst
            totals['sgst']    += sgst
            totals['total']   += total

        return Response({
            'month':    month,
            'invoices': rows,
            'totals': {k: str(round(v, 2)) for k, v in totals.items()},
        })


# ── CSV Export ────────────────────────────────────────────────────────────────

class ExportCSVView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store = _store(request)
        if not store:
            return Response({'detail': 'No store.'}, status=404)

        report_type = request.query_params.get('type', 'top-products')
        month       = request.query_params.get('month', str(date.today())[:7])

        buf = io.StringIO()
        writer = csv.writer(buf)

        if report_type == 'gst':
            view = GSTReportView()
            data = view.get(request).data
            writer.writerow(['Invoice ID', 'Date', 'Customer', 'GSTIN', 'GST Rate', 'Taxable', 'CGST', 'SGST', 'Total GST', 'Invoice Total'])
            for r in data.get('invoices', []):
                writer.writerow([r['invoice_id'], r['date'], r['customer'], r['gstin'], r['gst_rate'], r['taxable'], r['cgst'], r['sgst'], r['total_gst'], r['invoice_total']])

        elif report_type == 'top-products':
            view = TopProductsView()
            data = view.get(request).data
            writer.writerow(['Product', 'Qty Sold', 'Revenue (₹)', 'Revenue Share'])
            for p in data.get('products', []):
                writer.writerow([p['name'], p['qty'], p['revenue'], p['share']])

        elif report_type == 'abc':
            view = ABCAnalysisView()
            data = view.get(request).data
            writer.writerow(['Product', 'Revenue (₹)', 'Qty', 'Cumulative %', 'Tier'])
            for p in data.get('products', []):
                writer.writerow([p['name'], p['revenue'], p['qty'], p['cumulative'], p['tier']])

        elif report_type == 'gross-margin':
            view = GrossMarginView()
            data = view.get(request).data
            writer.writerow(['Product', 'Qty', 'Revenue (₹)', 'COGS (₹)', 'Gross Profit (₹)', 'Margin'])
            for p in data.get('products', []):
                writer.writerow([p['name'], p['qty'], p['revenue'], p['cogs'] or '', p['gross_profit'] or '', p['margin']])

        elif report_type == 'pnl':
            view = PnLView()
            data = view.get(request).data
            writer.writerow(['Month', 'Revenue', 'COGS', 'Gross Profit', 'Gross Margin', 'Expenses', 'Net Profit', 'Net Margin'])
            writer.writerow([data['month'], data['revenue'], data['cogs'], data['gross_profit'], data['gross_margin'], data['total_expenses'], data['net_profit'], data['net_margin']])

        else:
            return Response({'detail': f'Unknown report type: {report_type}'}, status=400)

        response = HttpResponse(buf.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_{month}.csv"'
        return response
