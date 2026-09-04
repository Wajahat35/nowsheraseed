import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction, models

from .models import ChartOfAccount, JournalVoucher, JournalItem, AccountCategory
from .forms import ChartOfAccountForm, JournalVoucherForm
from apps.accounts.views import log_activity, AdminRequiredMixin
from apps.reports.excel_generator import render_to_excel
from apps.reports.pdf_generator import render_to_pdf


class COAListView(LoginRequiredMixin, ListView):
    model = ChartOfAccount
    template_name = 'finance/coa_list.html'
    context_object_name = 'accounts'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = AccountCategory.objects.all()
        return context


class COACreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = ChartOfAccount
    form_class = ChartOfAccountForm
    template_name = 'finance/coa_form.html'
    success_url = reverse_lazy('finance:coa_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATE', 'Finance', f"Added COA Account {self.object.code} - {self.object.name}", self.request)
        messages.success(self.request, f"Account {self.object.name} added to COA.")
        return response


class VoucherListView(LoginRequiredMixin, ListView):
    model = JournalVoucher
    template_name = 'finance/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 25

    def get_queryset(self):
        qs = JournalVoucher.objects.all().select_related('created_by')
        vtype = self.request.GET.get('vtype')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        search = self.request.GET.get('search')

        if vtype:
            qs = qs.filter(voucher_type=vtype)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        if search:
            qs = qs.filter(
                models.Q(voucher_number__icontains=search) |
                models.Q(reference_no__icontains=search) |
                models.Q(description__icontains=search) |
                models.Q(items__narration__icontains=search) |
                models.Q(items__account__name__icontains=search) |
                models.Q(items__account__code__icontains=search)
            ).distinct()

        return qs.order_by('-date', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vtype'] = self.request.GET.get('vtype', '')
        context['search'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['voucher_types'] = JournalVoucher.VOUCHER_TYPES
        return context


class VoucherCreateView(LoginRequiredMixin, View):
    template_name = 'finance/voucher_form.html'

    def get(self, request):
        form = JournalVoucherForm()
        accounts = ChartOfAccount.objects.filter(is_active=True)
        return render(request, self.template_name, {
            'form': form,
            'accounts': accounts,
            'voucher': None,
            'existing_items_json': '[]',
        })

    def post(self, request):
        form = JournalVoucherForm(request.POST)
        items_data = request.POST.get('items_data')

        if form.is_valid() and items_data:
            try:
                raw_items = json.loads(items_data)
                items_list = [i for i in raw_items if i.get('account_id')]
                if not items_list:
                    messages.error(request, "Voucher must contain at least one line entry.")
                    return redirect('finance:voucher_create')

                with transaction.atomic():
                    voucher = form.save(commit=False)
                    voucher.created_by = request.user
                    voucher.save()

                    total_dr = Decimal('0.00')
                    total_cr = Decimal('0.00')

                    for item in items_list:
                        acc_id = item.get('account_id')
                        debit = Decimal(str(item.get('debit', 0) or 0))
                        credit = Decimal(str(item.get('credit', 0) or 0))
                        narration = (item.get('narration') or item.get('description') or '').strip()

                        account = ChartOfAccount.objects.get(id=acc_id)
                        total_dr += debit
                        total_cr += credit

                        JournalItem.objects.create(
                            voucher=voucher,
                            account=account,
                            debit=debit,
                            credit=credit,
                            narration=narration
                        )

                    voucher.total_debit = total_dr
                    voucher.total_credit = total_cr
                    voucher.save()

                    diff = abs(total_dr - total_cr)
                    status_str = "UNBALANCED" if total_dr != total_cr else "BALANCED"
                    log_activity(request.user, 'CREATE', 'Finance', f"Created {status_str} Journal Voucher {voucher.voucher_number} (Dr: PKR {total_dr}, Cr: PKR {total_cr}, Diff: PKR {diff})", request)
                    if total_dr != total_cr:
                        messages.warning(request, f"Journal Voucher {voucher.voucher_number} posted as UNBALANCED (Debit: PKR {total_dr} | Credit: PKR {total_cr} | Diff: PKR {diff}).")
                    else:
                        messages.success(request, f"Journal Voucher {voucher.voucher_number} posted successfully!")
                    return redirect('finance:voucher_detail', pk=voucher.pk)

            except Exception as e:
                messages.error(request, f"Error saving voucher: {str(e)}")

        return redirect('finance:voucher_create')


class VoucherUpdateView(LoginRequiredMixin, View):
    template_name = 'finance/voucher_form.html'

    def get(self, request, pk):
        voucher = get_object_or_404(JournalVoucher, pk=pk)
        form = JournalVoucherForm(instance=voucher)
        accounts = ChartOfAccount.objects.filter(is_active=True)

        items_list = []
        for item in voucher.items.all():
            items_list.append({
                'account_id': item.account.id,
                'account_name': f"{item.account.code} - {item.account.name}",
                'debit': float(item.debit),
                'credit': float(item.credit),
                'narration': item.narration or '',
                'description': item.narration or ''
            })

        return render(request, self.template_name, {
            'form': form,
            'accounts': accounts,
            'voucher': voucher,
            'existing_items_json': json.dumps(items_list),
        })

    def post(self, request, pk):
        voucher = get_object_or_404(JournalVoucher, pk=pk)
        form = JournalVoucherForm(request.POST, instance=voucher)
        items_data = request.POST.get('items_data')

        if form.is_valid() and items_data:
            try:
                raw_items = json.loads(items_data)
                items_list = [i for i in raw_items if i.get('account_id')]
                if not items_list:
                    messages.error(request, "Voucher must contain at least one line entry.")
                    return redirect('finance:voucher_edit', pk=pk)

                with transaction.atomic():
                    vch = form.save()
                    vch.items.all().delete()

                    total_dr = Decimal('0.00')
                    total_cr = Decimal('0.00')

                    for item in items_list:
                        acc_id = item.get('account_id')
                        debit = Decimal(str(item.get('debit', 0) or 0))
                        credit = Decimal(str(item.get('credit', 0) or 0))
                        narration = (item.get('narration') or item.get('description') or '').strip()

                        account = ChartOfAccount.objects.get(id=acc_id)
                        total_dr += debit
                        total_cr += credit

                        JournalItem.objects.create(
                            voucher=vch,
                            account=account,
                            debit=debit,
                            credit=credit,
                            narration=narration
                        )

                    vch.total_debit = total_dr
                    vch.total_credit = total_cr
                    vch.save()

                    diff = abs(total_dr - total_cr)
                    status_str = "UNBALANCED" if total_dr != total_cr else "BALANCED"
                    log_activity(request.user, 'UPDATE', 'Finance', f"Updated {status_str} Journal Voucher {vch.voucher_number} (Dr: PKR {total_dr}, Cr: PKR {total_cr}, Diff: PKR {diff})", request)
                    if total_dr != total_cr:
                        messages.warning(request, f"Journal Voucher {vch.voucher_number} updated as UNBALANCED (Debit: PKR {total_dr} | Credit: PKR {total_cr} | Diff: PKR {diff}).")
                    else:
                        messages.success(request, f"Journal Voucher {vch.voucher_number} updated successfully!")
                    return redirect('finance:voucher_detail', pk=vch.pk)

            except Exception as e:
                messages.error(request, f"Error updating voucher: {str(e)}")

        return redirect('finance:voucher_edit', pk=pk)


class VoucherDeleteView(LoginRequiredMixin, DeleteView):
    model = JournalVoucher
    success_url = reverse_lazy('finance:voucher_list')

    def delete(self, request, *args, **kwargs):
        voucher = self.get_object()
        log_activity(request.user, 'DELETE', 'Finance', f"Deleted Journal Voucher {voucher.voucher_number}", request)
        messages.success(request, f"Journal Voucher {voucher.voucher_number} deleted.")
        return super().delete(request, *args, **kwargs)


class VoucherDetailView(LoginRequiredMixin, DetailView):
    model = JournalVoucher
    template_name = 'finance/voucher_detail.html'
    context_object_name = 'voucher'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        voucher = self.get_object()
        running_bal = Decimal('0.00')
        items_with_balance = []
        for item in voucher.items.all().select_related('account'):
            running_bal += (item.debit - item.credit)
            items_with_balance.append({
                'item': item,
                'running_balance': running_bal,
                'abs_balance': abs(running_bal),
                'balance_type': 'Dr' if running_bal > 0 else ('Cr' if running_bal < 0 else 'Bal')
            })
        context['items_with_balance'] = items_with_balance
        return context


class ExportVoucherListExcelView(LoginRequiredMixin, View):
    def get(self, request):
        qs = JournalVoucher.objects.all().select_related('created_by').order_by('-date', '-id')
        vtype = request.GET.get('vtype')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        search = request.GET.get('search')

        if vtype:
            qs = qs.filter(voucher_type=vtype)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        if search:
            qs = qs.filter(
                models.Q(voucher_number__icontains=search) |
                models.Q(reference_no__icontains=search) |
                models.Q(description__icontains=search) |
                models.Q(items__narration__icontains=search) |
                models.Q(items__account__name__icontains=search) |
                models.Q(items__account__code__icontains=search)
            ).distinct()

        headers = ['Voucher #', 'Type', 'Date', 'Reference #', 'Description', 'Total Debit (PKR)', 'Total Credit (PKR)', 'Balance Diff (PKR)', 'Status', 'Created By']
        rows = []
        for v in qs:
            status = "BALANCED" if v.is_balanced else "UNBALANCED"
            rows.append([
                v.voucher_number,
                v.get_voucher_type_display(),
                str(v.date),
                v.reference_no or '',
                v.description or '',
                float(v.total_debit),
                float(v.total_credit),
                float(v.balance_difference),
                status,
                v.created_by.username if v.created_by else 'System'
            ])
        log_activity(request.user, 'EXPORT', 'Finance', 'Exported Journal Vouchers list to Excel', request)
        return render_to_excel('journal_vouchers_list.xlsx', 'Journal Vouchers', headers, rows)


class ExportVoucherListPDFView(LoginRequiredMixin, View):
    def get(self, request):
        qs = JournalVoucher.objects.all().order_by('-date', '-id')
        vtype = request.GET.get('vtype')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        search = request.GET.get('search')

        if vtype:
            qs = qs.filter(voucher_type=vtype)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        if search:
            qs = qs.filter(
                models.Q(voucher_number__icontains=search) |
                models.Q(reference_no__icontains=search) |
                models.Q(description__icontains=search) |
                models.Q(items__narration__icontains=search) |
                models.Q(items__account__name__icontains=search) |
                models.Q(items__account__code__icontains=search)
            ).distinct()

        headers = ['Voucher #', 'Type', 'Date', 'Ref #', 'Description', 'Debit (PKR)', 'Credit (PKR)', 'Diff (PKR)', 'Status']
        rows = []
        for v in qs:
            status = "Balanced" if v.is_balanced else "Unbalanced"
            rows.append([
                v.voucher_number,
                v.voucher_type,
                str(v.date),
                v.reference_no or '-',
                (v.description[:30] + '...') if v.description and len(v.description) > 30 else (v.description or '-'),
                f"{v.total_debit:,.2f}",
                f"{v.total_credit:,.2f}",
                f"{v.balance_difference:,.2f}",
                status
            ])
        log_activity(request.user, 'EXPORT', 'Finance', 'Exported Journal Vouchers list to PDF', request)
        return render_to_pdf('journal_vouchers_list.pdf', 'Journal Vouchers Report', headers, rows)


class ExportVoucherDetailExcelView(LoginRequiredMixin, View):
    def get(self, request, pk):
        voucher = get_object_or_404(JournalVoucher, pk=pk)
        headers = ['Description', 'Debit (PKR)', 'Credit (PKR)', 'Balance (PKR)']
        rows = []
        running_bal = Decimal('0.00')
        for item in voucher.items.all().select_related('account'):
            running_bal += (item.debit - item.credit)
            desc = f"{item.account.code} - {item.account.name}"
            if item.narration:
                desc += f" | {item.narration}"
            bal_str = f"PKR {abs(running_bal):,.2f} ({'Dr' if running_bal > 0 else ('Cr' if running_bal < 0 else 'Bal')})"
            rows.append([
                desc,
                float(item.debit),
                float(item.credit),
                bal_str
            ])
        rows.append(['TOTALS', float(voucher.total_debit), float(voucher.total_credit), f"Diff: PKR {voucher.balance_difference:,.2f}"])
        if not voucher.is_balanced:
            rows.append(['STATUS: UNBALANCED VOUCHER', '', '', f"Diff: PKR {voucher.balance_difference:,.2f}"])
        else:
            rows.append(['STATUS: BALANCED VOUCHER', '', '', 'PKR 0.00'])

        filename = f"Voucher_{voucher.voucher_number}.xlsx"
        sheet_title = f"{voucher.voucher_number}"
        log_activity(request.user, 'EXPORT', 'Finance', f"Exported Journal Voucher {voucher.voucher_number} to Excel", request)
        return render_to_excel(filename, sheet_title, headers, rows)


class ExportVoucherDetailPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        voucher = get_object_or_404(JournalVoucher, pk=pk)
        headers = ['Description', 'Debit (PKR)', 'Credit (PKR)', 'Balance (PKR)']
        rows = []
        running_bal = Decimal('0.00')
        for item in voucher.items.all().select_related('account'):
            running_bal += (item.debit - item.credit)
            desc = f"{item.account.code} - {item.account.name}"
            if item.narration:
                desc += f" ({item.narration})"
            bal_str = f"{abs(running_bal):,.2f} {'Dr' if running_bal > 0 else ('Cr' if running_bal < 0 else 'Bal')}"
            rows.append([
                desc,
                f"{item.debit:,.2f}" if item.debit > 0 else "-",
                f"{item.credit:,.2f}" if item.credit > 0 else "-",
                bal_str
            ])
        rows.append([
            'TOTALS',
            f"{voucher.total_debit:,.2f}",
            f"{voucher.total_credit:,.2f}",
            f"Diff: {voucher.balance_difference:,.2f}"
        ])
        status_str = "Balanced" if voucher.is_balanced else f"UNBALANCED (Diff: PKR {voucher.balance_difference:,.2f})"
        title = f"Journal Voucher {voucher.voucher_number} ({voucher.get_voucher_type_display()}) [{status_str}]"
        filename = f"Voucher_{voucher.voucher_number}.pdf"
        log_activity(request.user, 'EXPORT', 'Finance', f"Exported Journal Voucher {voucher.voucher_number} to PDF", request)
        return render_to_pdf(filename, title, headers, rows)


class GeneralLedgerView(LoginRequiredMixin, View):
    """Full Double-Entry General Ledger Report View with Account filter, Running Balances & Date Range."""
    template_name = 'finance/general_ledger.html'

    def get(self, request):
        account_id = request.GET.get('account')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        accounts = ChartOfAccount.objects.filter(is_active=True)
        selected_account = None
        ledger_entries = []
        tot_debit = Decimal('0.00')
        tot_credit = Decimal('0.00')
        running_balance = Decimal('0.00')

        if account_id:
            selected_account = ChartOfAccount.objects.filter(id=account_id).first()

        if selected_account:
            qs = JournalItem.objects.filter(account=selected_account).select_related('voucher').order_by('voucher__date', 'id')
            if start_date:
                qs = qs.filter(voucher__date__gte=start_date)
            if end_date:
                qs = qs.filter(voucher__date__lte=end_date)

            is_asset_exp = selected_account.category.name in ['ASSET', 'EXPENSE']

            for item in qs:
                tot_debit += item.debit
                tot_credit += item.credit

                if is_asset_exp:
                    running_balance += (item.debit - item.credit)
                else:
                    running_balance += (item.credit - item.debit)

                ledger_entries.append({
                    'id': item.id,
                    'date': item.voucher.date,
                    'voucher_number': item.voucher.voucher_number,
                    'voucher_type': item.voucher.voucher_type,
                    'voucher_pk': item.voucher.pk,
                    'narration': item.narration or item.voucher.description,
                    'debit': item.debit,
                    'credit': item.credit,
                    'running_balance': running_balance,
                })

        context = {
            'accounts': accounts,
            'selected_account': selected_account,
            'ledger_entries': ledger_entries,
            'total_debit': tot_debit,
            'total_credit': tot_credit,
            'final_balance': running_balance,
            'start_date': start_date,
            'end_date': end_date,
        }
        return render(request, self.template_name, context)


class TrialBalanceView(LoginRequiredMixin, View):
    template_name = 'finance/trial_balance.html'

    def get(self, request):
        accounts = ChartOfAccount.objects.filter(is_active=True)
        tb_data = []
        total_dr = Decimal('0.00')
        total_cr = Decimal('0.00')

        for acc in accounts:
            dr = JournalItem.objects.filter(account=acc).aggregate(t=models.Sum('debit'))['t'] or Decimal('0.00')
            cr = JournalItem.objects.filter(account=acc).aggregate(t=models.Sum('credit'))['t'] or Decimal('0.00')
            if dr > 0 or cr > 0:
                tb_data.append({
                    'id': acc.id,
                    'code': acc.code,
                    'name': acc.name,
                    'category': acc.category.get_name_display(),
                    'debit': dr,
                    'credit': cr,
                })
                total_dr += dr
                total_cr += cr

        context = {
            'tb_data': tb_data,
            'total_debit': total_dr,
            'total_credit': total_cr,
        }
        return render(request, self.template_name, context)


class ProfitLossView(LoginRequiredMixin, View):
    template_name = 'finance/profit_loss.html'

    def get(self, request):
        revenue_accs = ChartOfAccount.objects.filter(category__name='REVENUE')
        expense_accs = ChartOfAccount.objects.filter(category__name='EXPENSE')

        total_revenue = sum(acc.get_balance() for acc in revenue_accs)
        total_expenses = sum(acc.get_balance() for acc in expense_accs)
        net_profit = total_revenue - total_expenses

        context = {
            'revenue_accounts': revenue_accs,
            'expense_accounts': expense_accs,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
        }
        return render(request, self.template_name, context)


class BalanceSheetView(LoginRequiredMixin, View):
    template_name = 'finance/balance_sheet.html'

    def get(self, request):
        asset_accs = ChartOfAccount.objects.filter(category__name='ASSET')
        liab_accs = ChartOfAccount.objects.filter(category__name='LIABILITY')
        eq_accs = ChartOfAccount.objects.filter(category__name='EQUITY')

        total_assets = sum(acc.get_balance() for acc in asset_accs)
        total_liabilities = sum(acc.get_balance() for acc in liab_accs)
        total_equity = sum(acc.get_balance() for acc in eq_accs)

        context = {
            'asset_accounts': asset_accs,
            'liability_accounts': liab_accs,
            'equity_accounts': eq_accs,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
        }
        return render(request, self.template_name, context)


class CashBookView(LoginRequiredMixin, View):
    template_name = 'finance/cash_book.html'

    def get(self, request):
        cash_account = ChartOfAccount.objects.filter(code='1000').first()
        items = JournalItem.objects.filter(account=cash_account).select_related('voucher').order_by('voucher__date') if cash_account else []
        return render(request, self.template_name, {'items': items, 'account': cash_account})


class BankBookView(LoginRequiredMixin, View):
    template_name = 'finance/bank_book.html'

    def get(self, request):
        bank_account = ChartOfAccount.objects.filter(code='1010').first()
        items = JournalItem.objects.filter(account=bank_account).select_related('voucher').order_by('voucher__date') if bank_account else []
        return render(request, self.template_name, {'items': items, 'account': bank_account})
