from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from decimal import Decimal

from .models import Expense, ExpenseCategory
from .forms import ExpenseForm, ExpenseCategoryForm
from apps.accounts.views import log_activity
from apps.finance.models import ChartOfAccount, JournalVoucher, JournalItem


DEFAULT_EXPENSE_CATEGORIES = [
    ("Utility Bills", "Electricity, Water, Gas and Internet bills"),
    ("Office & Warehouse Rent", "Building and storage facility rent"),
    ("Staff Salaries & Wages", "Employee salaries, overtime, and daily labor wages"),
    ("Transport & Freight", "Logistics, cargo, and delivery expenses"),
    ("Fuel & Vehicle Maintenance", "Diesel, petrol, oil, and vehicle repairs"),
    ("Office Supplies & Stationery", "Paper, printing, pens, and office consumables"),
    ("Seed Testing & Certification", "FSC&RD lab fees, quality testing, and tags"),
    ("Packaging & Bagging Supplies", "Bags, thread, stencils, and packaging materials"),
    ("Repair & Maintenance", "Machinery, generator, and facility maintenance"),
    ("Meals & Refreshments", "Staff tea, meals, and entertainment"),
    ("Miscellaneous Expenses", "Other operational and administrative expenses"),
]


def ensure_default_expense_categories():
    """Ensure standard seed ERP expense categories exist in DB."""
    if ExpenseCategory.objects.count() == 0:
        for name, desc in DEFAULT_EXPENSE_CATEGORIES:
            ExpenseCategory.objects.get_or_create(name=name, defaults={'description': desc})


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 20

    def get_queryset(self):
        ensure_default_expense_categories()
        qs = Expense.objects.select_related('category', 'account').all()
        cat = self.request.GET.get('cat')
        search = self.request.GET.get('search')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if cat:
            qs = qs.filter(category_id=cat)
        if search:
            qs = qs.filter(description__icontains=search) | qs.filter(reference_no__icontains=search)
        if start_date:
            from django.utils.dateparse import parse_date
            s = parse_date(start_date)
            if s:
                qs = qs.filter(date__gte=s)
        if end_date:
            from django.utils.dateparse import parse_date
            e = parse_date(end_date)
            if e:
                qs = qs.filter(date__lte=e)
        return qs.order_by('-date', '-id')

    def get(self, request, *args, **kwargs):
        from apps.reports.pdf_generator import render_to_pdf
        from apps.reports.excel_generator import render_to_excel
        ensure_default_expense_categories()
        export_fmt = request.GET.get('export')
        if export_fmt in ('pdf', 'excel'):
            qs = self.get_queryset()
            start = request.GET.get('start_date', '')
            end = request.GET.get('end_date', '')
            period_label = ''
            if start and end:
                period_label = f' ({start} to {end})'
            elif start:
                period_label = f' (From {start})'
            elif end:
                period_label = f' (Up to {end})'
            if export_fmt == 'pdf':
                headers = ['Date', 'Category', 'Description', 'Payment Method', 'Ref #', 'Amount (PKR)']
                rows = [[str(e.date), e.category.name, e.description, e.payment_method, e.reference_no or '-', f'PKR {e.amount:,.2f}'] for e in qs]
                return render_to_pdf(f'expense_report.pdf', f'Operational Expenses Report{period_label}', headers, rows)
            elif export_fmt == 'excel':
                headers = ['Date', 'Category', 'Description', 'Payment Method', 'Ref #', 'Amount']
                rows = [[str(e.date), e.category.name, e.description, e.payment_method, e.reference_no or '', float(e.amount)] for e in qs]
                return render_to_excel('expense_report.xlsx', 'ExpensesReport', headers, rows)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ensure_default_expense_categories()
        context['categories'] = ExpenseCategory.objects.all()
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        # Total for filtered results
        from django.db.models import Sum
        total = self.get_queryset().aggregate(total=Sum('amount'))['total'] or 0
        context['total_amount'] = total
        return context

def post_expense_journal_voucher(expense, user):
    """Post or update double-entry journal voucher for an operational expense."""
    cash_acc = ChartOfAccount.objects.filter(code='1000').first()
    bank_acc = ChartOfAccount.objects.filter(code='1010').first()
    default_exp_acc = ChartOfAccount.objects.filter(category__name='EXPENSE').first()

    dr_account = expense.account or default_exp_acc
    cr_account = bank_acc if expense.payment_method in ['Bank', 'Online Transfer', 'Cheque'] else cash_acc

    if not dr_account or not cr_account:
        return

    ref_str = f"EXPV-{expense.id}"
    voucher = JournalVoucher.objects.filter(reference_no=ref_str).first()
    if not voucher:
        voucher = JournalVoucher(
            voucher_type='EXPV',
            date=expense.date,
            reference_no=ref_str,
            description=f"Expense: {expense.category.name} — {expense.description}",
            created_by=user
        )
        voucher.save()
    else:
        voucher.date = expense.date
        voucher.description = f"Expense: {expense.category.name} — {expense.description}"
        voucher.save()
        voucher.items.all().delete()

    amt = Decimal(str(expense.amount))

    # Debit Expense Account
    JournalItem.objects.create(
        voucher=voucher,
        account=dr_account,
        debit=amt,
        credit=Decimal('0.00'),
        narration=f"{expense.category.name}: {expense.description}"
    )

    # Credit Cash/Bank Account
    JournalItem.objects.create(
        voucher=voucher,
        account=cr_account,
        debit=Decimal('0.00'),
        credit=amt,
        narration=f"Payment for {expense.category.name} ({expense.payment_method})"
    )

    voucher.total_debit = amt
    voucher.total_credit = amt
    voucher.save()


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:expense_list')

    def get(self, request, *args, **kwargs):
        ensure_default_expense_categories()
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.created_by = self.request.user
            response = super().form_valid(form)
            post_expense_journal_voucher(self.object, self.request.user)

        log_activity(self.request.user, 'CREATE', 'Expenses', f"Added Expense {self.object.category.name} (PKR {self.object.amount})", self.request)
        messages.success(self.request, f"Expense PKR {self.object.amount:,.2f} recorded and posted to Double-Entry Ledger!")
        return response


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:expense_list')

    def get(self, request, *args, **kwargs):
        ensure_default_expense_categories()
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            post_expense_journal_voucher(self.object, self.request.user)

        log_activity(self.request.user, 'UPDATE', 'Expenses', f"Updated Expense #{self.object.pk} ({self.object.category.name})", self.request)
        messages.success(self.request, f"Expense #{self.object.pk} updated successfully!")
        return response


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    success_url = reverse_lazy('expenses:expense_list')

    def delete(self, request, *args, **kwargs):
        expense = self.get_object()
        ref_str = f"EXPV-{expense.id}"
        JournalVoucher.objects.filter(reference_no=ref_str).delete()
        log_activity(request.user, 'DELETE', 'Expenses', f"Deleted Expense #{expense.id} ({expense.category.name})", request)
        messages.success(request, f"Expense #{expense.id} deleted.")
        return super().delete(request, *args, **kwargs)


class QuickAddCategoryView(LoginRequiredMixin, View):
    """API view to quickly add an expense category via modal/AJAX."""
    def post(self, request):
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            return JsonResponse({'success': False, 'error': 'Category name is required.'})

        category, created = ExpenseCategory.objects.get_or_create(
            name__iexact=name,
            defaults={'name': name, 'description': description}
        )

        return JsonResponse({
            'success': True,
            'id': category.id,
            'name': category.name,
            'created': created
        })


class ExpenseCategoryListView(LoginRequiredMixin, ListView):
    model = ExpenseCategory
    template_name = 'expenses/expense_category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        ensure_default_expense_categories()
        return ExpenseCategory.objects.all()

    def post(self, request):
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense Category created!")
            return redirect('expenses:category_list')
        return self.get(request)
