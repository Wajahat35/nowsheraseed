import csv
import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import models

from .models import TradingAccount, Deposit, Withdrawal, Trade
from .forms import TradingAccountForm, DepositForm, WithdrawalForm, TradeForm
from .services import calculate_trading_stats
from apps.accounts.views import log_activity
from apps.reports.excel_generator import render_to_excel
from apps.reports.pdf_generator import render_to_pdf


class TradingAccessRequiredMixin(UserPassesTestMixin):
    """Protects Trading views — user must have trading access or be superuser."""
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_superuser or getattr(user, 'can_access_trading', True))

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('accounts:login')
        messages.error(self.request, "Access Denied: You do not have permission to access the Trading Management System.")
        if getattr(self.request.user, 'has_seed_access', lambda: True)():
            return redirect('dashboard:home')
        return redirect('accounts:login')


class TradingDashboardView(LoginRequiredMixin, TradingAccessRequiredMixin, View):
    template_name = 'trading/dashboard.html'

    def get(self, request):
        stats = calculate_trading_stats()
        accounts = TradingAccount.objects.filter(is_active=True)[:6]
        recent_trades = Trade.objects.select_related('account').all()[:8]
        recent_deposits = Deposit.objects.select_related('account').all()[:5]
        recent_withdrawals = Withdrawal.objects.select_related('account').all()[:5]

        # Monthly performance chart data
        trades = Trade.objects.filter(status='Closed').order_by('trade_date')
        monthly_map = {}
        for t in trades:
            m_key = t.trade_date.strftime('%Y-%m')
            monthly_map[m_key] = monthly_map.get(m_key, Decimal('0.00')) + t.net_profit

        chart_labels = list(monthly_map.keys())[-12:]
        chart_data = [float(monthly_map[k]) for k in chart_labels]

        context = {
            'stats': stats,
            'accounts': accounts,
            'recent_trades': recent_trades,
            'recent_deposits': recent_deposits,
            'recent_withdrawals': recent_withdrawals,
            'chart_labels_json': json.dumps(chart_labels),
            'chart_data_json': json.dumps(chart_data),
        }
        return render(request, self.template_name, context)


class TradingAccountListView(LoginRequiredMixin, TradingAccessRequiredMixin, ListView):
    model = TradingAccount
    template_name = 'trading/account_list.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        qs = TradingAccount.objects.all()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(broker_name__icontains=q) | qs.filter(account_number__icontains=q)
        return qs.order_by('-id')


class TradingAccountCreateView(LoginRequiredMixin, TradingAccessRequiredMixin, CreateView):
    model = TradingAccount
    form_class = TradingAccountForm
    template_name = 'trading/account_form.html'
    success_url = reverse_lazy('trading:account_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        self.object.recalculate_financials()
        log_activity(self.request.user, 'CREATE', 'Trading', f"Created Trading Account {self.object.name} (#{self.object.account_number})", self.request)
        messages.success(self.request, f"Trading Account '{self.object.name}' created successfully!")
        return response


class TradingAccountUpdateView(LoginRequiredMixin, TradingAccessRequiredMixin, UpdateView):
    model = TradingAccount
    form_class = TradingAccountForm
    template_name = 'trading/account_form.html'
    success_url = reverse_lazy('trading:account_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.recalculate_financials()
        log_activity(self.request.user, 'UPDATE', 'Trading', f"Updated Trading Account {self.object.name}", self.request)
        messages.success(self.request, f"Trading Account '{self.object.name}' updated successfully!")
        return response


class TradingAccountDeleteView(LoginRequiredMixin, TradingAccessRequiredMixin, DeleteView):
    model = TradingAccount
    template_name = 'trading/account_confirm_delete.html'
    success_url = reverse_lazy('trading:account_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_activity(request.user, 'DELETE', 'Trading', f"Deleted Trading Account {obj.name}", request)
        messages.success(request, f"Trading Account '{obj.name}' deleted.")
        return super().delete(request, *args, **kwargs)


class TradingAccountDetailView(LoginRequiredMixin, TradingAccessRequiredMixin, DetailView):
    model = TradingAccount
    template_name = 'trading/account_detail.html'
    context_object_name = 'account'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        acc = self.object
        acc.recalculate_financials()
        stats = calculate_trading_stats(account_id=acc.id)
        trades = acc.trades.all()[:15]
        deposits = acc.deposits.all()[:10]
        withdrawals = acc.withdrawals.all()[:10]
        context['stats'] = stats
        context['trades'] = trades
        context['deposits'] = deposits
        context['withdrawals'] = withdrawals
        return context


class TradingAccountToggleView(LoginRequiredMixin, TradingAccessRequiredMixin, View):
    def post(self, request, pk):
        acc = get_object_or_404(TradingAccount, pk=pk)
        acc.is_active = not acc.is_active
        acc.save()
        status_name = "Activated" if acc.is_active else "Deactivated"
        log_activity(request.user, 'UPDATE', 'Trading', f"{status_name} Trading Account {acc.name}", request)
        messages.info(request, f"Account '{acc.name}' has been {status_name}.")
        return redirect('trading:account_list')


# ---------------------------------------------------------------------------
# DEPOSITS VIEWS
# ---------------------------------------------------------------------------
class DepositListView(LoginRequiredMixin, TradingAccessRequiredMixin, ListView):
    model = Deposit
    template_name = 'trading/deposit_list.html'
    context_object_name = 'deposits'
    paginate_by = 20

    def get_queryset(self):
        qs = Deposit.objects.select_related('account').all()
        acc_id = self.request.GET.get('account')
        if acc_id:
            qs = qs.filter(account_id=acc_id)
        return qs.order_by('-deposit_date', '-id')


class DepositCreateView(LoginRequiredMixin, TradingAccessRequiredMixin, CreateView):
    model = Deposit
    form_class = DepositForm
    template_name = 'trading/deposit_form.html'
    success_url = reverse_lazy('trading:deposit_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATE', 'Trading', f"Added Deposit {self.object.currency} {self.object.amount} to {self.object.account.name}", self.request)
        messages.success(self.request, f"Deposit of {self.object.currency} {self.object.amount:,.2f} recorded successfully!")
        return response


class DepositUpdateView(LoginRequiredMixin, TradingAccessRequiredMixin, UpdateView):
    model = Deposit
    form_class = DepositForm
    template_name = 'trading/deposit_form.html'
    success_url = reverse_lazy('trading:deposit_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'UPDATE', 'Trading', f"Updated Deposit #{self.object.id}", self.request)
        messages.success(self.request, "Deposit updated successfully!")
        return response


class DepositDeleteView(LoginRequiredMixin, TradingAccessRequiredMixin, DeleteView):
    model = Deposit
    template_name = 'trading/deposit_confirm_delete.html'
    success_url = reverse_lazy('trading:deposit_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_activity(request.user, 'DELETE', 'Trading', f"Deleted Deposit {obj.amount} for {obj.account.name}", request)
        messages.success(request, f"Deposit deleted successfully.")
        return super().delete(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# WITHDRAWALS VIEWS
# ---------------------------------------------------------------------------
class WithdrawalListView(LoginRequiredMixin, TradingAccessRequiredMixin, ListView):
    model = Withdrawal
    template_name = 'trading/withdrawal_list.html'
    context_object_name = 'withdrawals'
    paginate_by = 20

    def get_queryset(self):
        qs = Withdrawal.objects.select_related('account').all()
        acc_id = self.request.GET.get('account')
        if acc_id:
            qs = qs.filter(account_id=acc_id)
        return qs.order_by('-withdrawal_date', '-id')


class WithdrawalCreateView(LoginRequiredMixin, TradingAccessRequiredMixin, CreateView):
    model = Withdrawal
    form_class = WithdrawalForm
    template_name = 'trading/withdrawal_form.html'
    success_url = reverse_lazy('trading:withdrawal_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATE', 'Trading', f"Added Withdrawal {self.object.currency} {self.object.amount} from {self.object.account.name}", self.request)
        messages.success(self.request, f"Withdrawal of {self.object.currency} {self.object.amount:,.2f} recorded successfully!")
        return response


class WithdrawalUpdateView(LoginRequiredMixin, TradingAccessRequiredMixin, UpdateView):
    model = Withdrawal
    form_class = WithdrawalForm
    template_name = 'trading/withdrawal_form.html'
    success_url = reverse_lazy('trading:withdrawal_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'UPDATE', 'Trading', f"Updated Withdrawal #{self.object.id}", self.request)
        messages.success(self.request, "Withdrawal updated successfully!")
        return response


class WithdrawalDeleteView(LoginRequiredMixin, TradingAccessRequiredMixin, DeleteView):
    model = Withdrawal
    template_name = 'trading/withdrawal_confirm_delete.html'
    success_url = reverse_lazy('trading:withdrawal_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_activity(request.user, 'DELETE', 'Trading', f"Deleted Withdrawal {obj.amount} for {obj.account.name}", request)
        messages.success(request, "Withdrawal deleted.")
        return super().delete(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# TRADES VIEWS
# ---------------------------------------------------------------------------
class TradeListView(LoginRequiredMixin, TradingAccessRequiredMixin, ListView):
    model = Trade
    template_name = 'trading/trade_list.html'
    context_object_name = 'trades'
    paginate_by = 25

    def get_queryset(self):
        qs = Trade.objects.select_related('account').all()
        q_acc = self.request.GET.get('account')
        q_sym = self.request.GET.get('symbol')
        q_market = self.request.GET.get('market_type')
        q_dir = self.request.GET.get('direction')
        q_status = self.request.GET.get('status')
        q_search = self.request.GET.get('q')

        if q_acc:
            qs = qs.filter(account_id=q_acc)
        if q_sym:
            qs = qs.filter(symbol__icontains=q_sym)
        if q_market:
            qs = qs.filter(market_type=q_market)
        if q_dir:
            qs = qs.filter(direction=q_dir)
        if q_status:
            qs = qs.filter(status=q_status)
        if q_search:
            qs = qs.filter(models.Q(symbol__icontains=q_search) | models.Q(strategy__icontains=q_search) | models.Q(notes__icontains=q_search))

        return qs.order_by('-trade_date', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accounts'] = TradingAccount.objects.filter(is_active=True)
        context['stats'] = calculate_trading_stats()
        return context


class TradeCreateView(LoginRequiredMixin, TradingAccessRequiredMixin, CreateView):
    model = Trade
    form_class = TradeForm
    template_name = 'trading/trade_form.html'
    success_url = reverse_lazy('trading:trade_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATE', 'Trading', f"Added Trade {self.object.direction} {self.object.symbol} ({self.object.account.name})", self.request)
        messages.success(self.request, f"Trade '{self.object.direction} {self.object.symbol}' recorded successfully!")
        return response


class TradeUpdateView(LoginRequiredMixin, TradingAccessRequiredMixin, UpdateView):
    model = Trade
    form_class = TradeForm
    template_name = 'trading/trade_form.html'
    success_url = reverse_lazy('trading:trade_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'UPDATE', 'Trading', f"Updated Trade #{self.object.id} ({self.object.symbol})", self.request)
        messages.success(self.request, f"Trade '{self.object.symbol}' updated successfully!")
        return response


class TradeDeleteView(LoginRequiredMixin, TradingAccessRequiredMixin, DeleteView):
    model = Trade
    template_name = 'trading/trade_confirm_delete.html'
    success_url = reverse_lazy('trading:trade_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_activity(request.user, 'DELETE', 'Trading', f"Deleted Trade #{obj.id} ({obj.symbol})", request)
        messages.success(request, f"Trade deleted.")
        return super().delete(request, *args, **kwargs)


class TradeDetailView(LoginRequiredMixin, TradingAccessRequiredMixin, DetailView):
    model = Trade
    template_name = 'trading/trade_detail.html'
    context_object_name = 'trade'


# ---------------------------------------------------------------------------
# REPORTS & EXPORT VIEWS
# ---------------------------------------------------------------------------
class TradingReportsView(LoginRequiredMixin, TradingAccessRequiredMixin, View):
    template_name = 'trading/reports.html'

    def get(self, request):
        acc_id = request.GET.get('account')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        market_type = request.GET.get('market_type')
        symbol = request.GET.get('symbol')
        direction = request.GET.get('direction')
        status = request.GET.get('status')

        accounts = TradingAccount.objects.filter(is_active=True)
        stats = calculate_trading_stats(
            account_id=acc_id, date_from=date_from, date_to=date_to,
            market_type=market_type, symbol=symbol, direction=direction, status=status
        )

        trades = Trade.objects.select_related('account').all()
        if acc_id:
            trades = trades.filter(account_id=acc_id)
        if date_from:
            trades = trades.filter(trade_date__gte=date_from)
        if date_to:
            trades = trades.filter(trade_date__lte=date_to)
        if market_type:
            trades = trades.filter(market_type=market_type)
        if symbol:
            trades = trades.filter(symbol__icontains=symbol)
        if direction:
            trades = trades.filter(direction=direction)
        if status:
            trades = trades.filter(status=status)

        trades = trades.order_by('-trade_date')[:100]

        context = {
            'accounts': accounts,
            'stats': stats,
            'trades': trades,
            'acc_id': acc_id,
            'date_from': date_from,
            'date_to': date_to,
            'market_type': market_type,
            'symbol': symbol,
            'direction': direction,
            'status': status,
        }
        return render(request, self.template_name, context)


class ExportTradingCSVView(LoginRequiredMixin, TradingAccessRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="trading_history.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Account', 'Broker', 'Symbol', 'Market Type',
            'Direction', 'Lot Size', 'Entry Price', 'Exit Price',
            'Gross P/L', 'Commission', 'Swap Fee', 'Net P/L', 'Status', 'Strategy'
        ])

        trades = Trade.objects.select_related('account').all().order_by('-trade_date')
        for t in trades:
            writer.writerow([
                str(t.trade_date),
                t.account.name,
                t.account.broker_name,
                t.symbol,
                t.market_type,
                t.direction,
                float(t.lot_size),
                float(t.entry_price),
                float(t.exit_price) if t.exit_price else '',
                float(t.profit_loss),
                float(t.commission),
                float(t.swap_fee),
                float(t.net_profit),
                t.status,
                t.strategy or ''
            ])
        log_activity(request.user, 'EXPORT', 'Trading', 'Exported Trading History to CSV', request)
        return response


class ExportTradingExcelView(LoginRequiredMixin, TradingAccessRequiredMixin, View):
    def get(self, request):
        headers = [
            'Date', 'Account', 'Broker', 'Symbol', 'Market',
            'Buy/Sell', 'Lot Size', 'Entry Price', 'Exit Price',
            'Gross P/L', 'Commission', 'Swap', 'Net P/L ($)', 'Status'
        ]
        rows = []
        trades = Trade.objects.select_related('account').all().order_by('-trade_date')
        for t in trades:
            rows.append([
                str(t.trade_date),
                t.account.name,
                t.account.broker_name,
                t.symbol,
                t.market_type,
                t.direction,
                float(t.lot_size),
                float(t.entry_price),
                float(t.exit_price) if t.exit_price else '-',
                float(t.profit_loss),
                float(t.commission),
                float(t.swap_fee),
                float(t.net_profit),
                t.status
            ])
        log_activity(request.user, 'EXPORT', 'Trading', 'Exported Trading History to Excel', request)
        return render_to_excel('trading_performance.xlsx', 'Trading Performance', headers, rows)


class ExportTradingPDFView(LoginRequiredMixin, TradingAccessRequiredMixin, View):
    def get(self, request):
        headers = ['Date', 'Account', 'Symbol', 'Type', 'Buy/Sell', 'Lots', 'Net P/L ($)', 'Status']
        rows = []
        trades = Trade.objects.select_related('account').all().order_by('-trade_date')[:150]
        for t in trades:
            rows.append([
                str(t.trade_date),
                t.account.name[:15],
                t.symbol,
                t.market_type,
                t.direction,
                f"{t.lot_size:.2f}",
                f"${t.net_profit:,.2f}",
                t.status
            ])
        log_activity(request.user, 'EXPORT', 'Trading', 'Exported Trading Performance Report to PDF', request)
        return render_to_pdf('trading_performance_report.pdf', 'Trading Performance Report', headers, rows)
