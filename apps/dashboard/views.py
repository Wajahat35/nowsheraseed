import json
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.http import JsonResponse

from apps.sales.models import SalesInvoice, SalesItem
from apps.purchases.models import PurchaseInvoice
from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.seeds.models import Seed, SeedBatch
from apps.gatepass.models import GatePass
from apps.expenses.models import Expense


def get_dashboard_metrics():
    """Calculate real-time executive dashboard metrics including Daily, Monthly, Quarterly, and Yearly breakdowns."""
    today = timezone.now().date()
    current_year = today.year
    current_month = today.month

    # ── 1. Daily (Today) ──
    today_sales = float(SalesInvoice.objects.filter(date=today).aggregate(t=Sum('grand_total'))['t'] or 0)
    today_purchases = float(PurchaseInvoice.objects.filter(date=today).aggregate(t=Sum('grand_total'))['t'] or 0)

    # ── 2. Monthly (This Month) ──
    month_sales = float(SalesInvoice.objects.filter(
        date__year=current_year, date__month=current_month
    ).aggregate(t=Sum('grand_total'))['t'] or 0)

    month_purchases = float(PurchaseInvoice.objects.filter(
        date__year=current_year, date__month=current_month
    ).aggregate(t=Sum('grand_total'))['t'] or 0)

    # ── 3. Quarterly (This Quarter) ──
    current_quarter = (current_month - 1) // 3 + 1
    q_start_month = (current_quarter - 1) * 3 + 1
    q_end_month = current_quarter * 3

    quarter_sales = float(SalesInvoice.objects.filter(
        date__year=current_year, date__month__gte=q_start_month, date__month__lte=q_end_month
    ).aggregate(t=Sum('grand_total'))['t'] or 0)

    quarter_purchases = float(PurchaseInvoice.objects.filter(
        date__year=current_year, date__month__gte=q_start_month, date__month__lte=q_end_month
    ).aggregate(t=Sum('grand_total'))['t'] or 0)

    # ── 4. Yearly (This Year) ──
    year_sales = float(SalesInvoice.objects.filter(date__year=current_year).aggregate(t=Sum('grand_total'))['t'] or 0)
    year_purchases = float(PurchaseInvoice.objects.filter(date__year=current_year).aggregate(t=Sum('grand_total'))['t'] or 0)

    # ── Customer / Supplier Counts ──
    total_customers = Customer.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()

    # ── Seed Stock & Alerts ──
    all_seeds = list(Seed.objects.prefetch_related('batches').all())
    total_seed_stock = sum(s.get_total_stock() for s in all_seeds)
    low_stock_count = sum(1 for s in all_seeds if s.get_total_stock() <= s.min_stock_alert)

    all_batches = list(SeedBatch.objects.all())
    expired_stock_count = sum(1 for b in all_batches if b.is_expired() and b.current_qty > 0)

    # ── Financial Totals ──
    total_sales_revenue = float(SalesInvoice.objects.aggregate(t=Sum('grand_total'))['t'] or 0)
    total_purchase_cost = float(PurchaseInvoice.objects.aggregate(t=Sum('grand_total'))['t'] or 0)
    total_expenses = float(Expense.objects.aggregate(t=Sum('amount'))['t'] or 0)

    # ── Receivables & Payables ──
    pending_receivables = float(SalesInvoice.objects.filter(
        payment_status__in=['Unpaid', 'Partial']
    ).aggregate(t=Sum('grand_total') - Sum('paid_amount'))['t'] or 0)

    pending_payables = float(PurchaseInvoice.objects.filter(
        payment_status__in=['Unpaid', 'Partial']
    ).aggregate(t=Sum('grand_total') - Sum('paid_amount'))['t'] or 0)

    unpaid_sales_count = SalesInvoice.objects.filter(payment_status__in=['Unpaid', 'Partial']).count()
    unpaid_purchase_count = PurchaseInvoice.objects.filter(payment_status__in=['Unpaid', 'Partial']).count()

    gross_profit = total_sales_revenue - total_purchase_cost - total_expenses

    # ── Monthly Breakdown (Jan-Dec Current Year) ──
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_sales_arr = []
    monthly_purchases_arr = []
    for m in range(1, 13):
        ms = float(SalesInvoice.objects.filter(date__year=current_year, date__month=m).aggregate(t=Sum('grand_total'))['t'] or 0)
        mp = float(PurchaseInvoice.objects.filter(date__year=current_year, date__month=m).aggregate(t=Sum('grand_total'))['t'] or 0)
        monthly_sales_arr.append(ms)
        monthly_purchases_arr.append(mp)

    # ── Quarterly Breakdown (Q1..Q4 Current Year) ──
    quarter_labels = ['Q1 (Jan-Mar)', 'Q2 (Apr-Jun)', 'Q3 (Jul-Sep)', 'Q4 (Oct-Dec)']
    quarterly_sales_arr = []
    quarterly_purchases_arr = []
    for q in range(1, 5):
        qs_m_start = (q - 1) * 3 + 1
        qs_m_end = q * 3
        qs = float(SalesInvoice.objects.filter(date__year=current_year, date__month__gte=qs_m_start, date__month__lte=qs_m_end).aggregate(t=Sum('grand_total'))['t'] or 0)
        qp = float(PurchaseInvoice.objects.filter(date__year=current_year, date__month__gte=qs_m_start, date__month__lte=qs_m_end).aggregate(t=Sum('grand_total'))['t'] or 0)
        quarterly_sales_arr.append(qs)
        quarterly_purchases_arr.append(qp)

    # ── Daily Breakdown (Last 14 Days) ──
    daily_labels = []
    daily_sales_arr = []
    daily_purchases_arr = []
    for i in range(13, -1, -1):
        day_d = today - timedelta(days=i)
        daily_labels.append(day_d.strftime('%b %d'))
        ds = float(SalesInvoice.objects.filter(date=day_d).aggregate(t=Sum('grand_total'))['t'] or 0)
        dp = float(PurchaseInvoice.objects.filter(date=day_d).aggregate(t=Sum('grand_total'))['t'] or 0)
        daily_sales_arr.append(ds)
        daily_purchases_arr.append(dp)

    # ── Yearly Breakdown (Last 5 Years) ──
    yearly_labels = [str(current_year - i) for i in range(4, -1, -1)]
    yearly_sales_arr = []
    yearly_purchases_arr = []
    for yr_str in yearly_labels:
        yr = int(yr_str)
        ys = float(SalesInvoice.objects.filter(date__year=yr).aggregate(t=Sum('grand_total'))['t'] or 0)
        yp = float(PurchaseInvoice.objects.filter(date__year=yr).aggregate(t=Sum('grand_total'))['t'] or 0)
        yearly_sales_arr.append(ys)
        yearly_purchases_arr.append(yp)

    # ── Recent Transactions ──
    recent_invoices = list(SalesInvoice.objects.select_related('customer').order_by('-id')[:6].values(
        'id', 'invoice_number', 'customer__name', 'grand_total', 'payment_status', 'date'
    ))
    for inv in recent_invoices:
        inv['date'] = str(inv['date'])
        inv['grand_total'] = float(inv['grand_total'])

    recent_purchases = list(PurchaseInvoice.objects.select_related('supplier').order_by('-id')[:5].values(
        'id', 'invoice_number', 'supplier__name', 'grand_total', 'payment_status', 'date'
    ))
    for pur in recent_purchases:
        pur['date'] = str(pur['date'])
        pur['grand_total'] = float(pur['grand_total'])

    top_seeds = list(SalesItem.objects.values('seed__name').annotate(
        total_qty=Sum('quantity')
    ).order_by('-total_qty')[:6])

    return {
        # Periodic KPI Totals
        'today_sales': today_sales,
        'today_purchases': today_purchases,
        'month_sales': month_sales,
        'month_purchases': month_purchases,
        'quarter_sales': quarter_sales,
        'quarter_purchases': quarter_purchases,
        'year_sales': year_sales,
        'year_purchases': year_purchases,
        'current_quarter': current_quarter,
        'current_month': current_month,
        'current_year': current_year,

        # General Counts & Financials
        'total_customers': total_customers,
        'total_suppliers': total_suppliers,
        'total_seed_stock': total_seed_stock,
        'low_stock_count': low_stock_count,
        'expired_stock_count': expired_stock_count,
        'total_sales_revenue': total_sales_revenue,
        'total_purchase_cost': total_purchase_cost,
        'total_expenses': total_expenses,
        'gross_profit': gross_profit,

        # AR / AP
        'pending_receivables': pending_receivables,
        'pending_payables': pending_payables,
        'unpaid_sales_count': unpaid_sales_count,
        'unpaid_purchase_count': unpaid_purchase_count,

        # Chart Series
        'month_labels': month_labels,
        'monthly_sales': monthly_sales_arr,
        'monthly_purchases': monthly_purchases_arr,
        'quarter_labels': quarter_labels,
        'quarterly_sales': quarterly_sales_arr,
        'quarterly_purchases': quarterly_purchases_arr,
        'daily_labels': daily_labels,
        'daily_sales': daily_sales_arr,
        'daily_purchases': daily_purchases_arr,
        'yearly_labels': yearly_labels,
        'yearly_sales': yearly_sales_arr,
        'yearly_purchases': yearly_purchases_arr,

        # Lists
        'recent_invoices': recent_invoices,
        'recent_purchases': recent_purchases,
        'top_seeds': top_seeds,
    }


class DashboardHomeView(LoginRequiredMixin, View):
    template_name = 'dashboard/index.html'

    def get(self, request):
        metrics = get_dashboard_metrics()
        recent_gatepasses = GatePass.objects.order_by('-id')[:5]

        context = {
            **metrics,
            'recent_gatepasses': recent_gatepasses,
            'month_labels_json': json.dumps(metrics['month_labels']),
            'monthly_sales_json': json.dumps(metrics['monthly_sales']),
            'monthly_purchases_json': json.dumps(metrics['monthly_purchases']),
            'quarter_labels_json': json.dumps(metrics['quarter_labels']),
            'quarterly_sales_json': json.dumps(metrics['quarterly_sales']),
            'quarterly_purchases_json': json.dumps(metrics['quarterly_purchases']),
            'daily_labels_json': json.dumps(metrics['daily_labels']),
            'daily_sales_json': json.dumps(metrics['daily_sales']),
            'daily_purchases_json': json.dumps(metrics['daily_purchases']),
            'yearly_labels_json': json.dumps(metrics['yearly_labels']),
            'yearly_sales_json': json.dumps(metrics['yearly_sales']),
            'yearly_purchases_json': json.dumps(metrics['yearly_purchases']),
        }
        return render(request, self.template_name, context)


class DashboardApiView(LoginRequiredMixin, View):
    """Real-time JSON API endpoint for auto-updating dashboard data without full page refresh."""
    def get(self, request):
        metrics = get_dashboard_metrics()
        return JsonResponse({'success': True, 'metrics': metrics})

