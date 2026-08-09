from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views import View
from django.http import HttpResponse
import csv, io
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Customer
from .forms import CustomerForm
from apps.accounts.views import log_activity

class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        qs = Customer.objects.all()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q) | qs.filter(phone__icontains=q) | qs.filter(company_name__icontains=q)
        return qs.order_by('-id')

class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:customer_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATE', 'Customers', f"Created customer {self.object.name} ({self.object.code})", self.request)
        messages.success(self.request, f"Customer {self.object.name} added successfully!")
        return response

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:customer_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'UPDATE', 'Customers', f"Updated customer {self.object.name} ({self.object.code})", self.request)
        messages.success(self.request, f"Customer {self.object.name} updated successfully!")
        return response

class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customers/customer_confirm_delete.html'
    success_url = reverse_lazy('customers:customer_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_activity(request.user, 'DELETE', 'Customers', f"Deleted customer {obj.name} ({obj.code})", request)
        messages.success(request, f"Customer {obj.name} deleted.")
        return super().delete(request, *args, **kwargs)

class CustomerLedgerView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'customers/customer_ledger.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.sales.models import SalesInvoice
        customer = self.object
        invoices = SalesInvoice.objects.filter(customer=customer).order_by('date')
        
        # Build ledger statement timeline
        ledger_entries = []
        running_balance = customer.opening_balance
        
        if customer.opening_balance != 0:
            ledger_entries.append({
                'date': customer.created_at,
                'reference': 'OPENING BALANCE',
                'description': 'Customer Opening Balance',
                'debit': customer.opening_balance if customer.opening_balance > 0 else 0,
                'credit': abs(customer.opening_balance) if customer.opening_balance < 0 else 0,
                'balance': running_balance
            })
            
        for inv in invoices:
            running_balance += inv.grand_total
            ledger_entries.append({
                'date': inv.date,
                'reference': inv.invoice_number,
                'description': f"Sales Invoice - {inv.get_sales_type_display()}",
                'debit': inv.grand_total,
                'credit': 0,
                'balance': running_balance,
                'url': inv.get_absolute_url() if hasattr(inv, 'get_absolute_url') else None
            })
            if inv.paid_amount > 0:
                running_balance -= inv.paid_amount
                ledger_entries.append({
                    'date': inv.date,
                    'reference': f"RCPT-{inv.invoice_number}",
                    'description': f"Payment Received ({inv.payment_method})",
                    'debit': 0,
                    'credit': inv.paid_amount,
                    'balance': running_balance
                })

        context['ledger_entries'] = ledger_entries
        context['current_balance'] = running_balance
        return context


class CustomerBulkUploadView(LoginRequiredMixin, View):
    template_name = 'customers/customer_bulk_upload.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return render(request, self.template_name)
        try:
            decoded = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
            created = 0
            skipped = 0
            for row_num, row in enumerate(reader, start=2):
                name = row.get('name', '').strip()
                phone = row.get('phone', '').strip()
                if not name or not phone:
                    skipped += 1
                    continue
                _, was_created = Customer.objects.get_or_create(
                    name=name, phone=phone,
                    defaults={
                        'company_name': row.get('company_name', '').strip() or None,
                        'city': row.get('city', 'Lahore').strip() or 'Lahore',
                        'email': row.get('email', '').strip() or None,
                        'address': row.get('address', '').strip() or None,
                        'opening_balance': float(row.get('opening_balance', '0') or '0'),
                    }
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1
            messages.success(request, f'Upload complete: {created} customers created, {skipped} skipped/duplicates.')
            log_activity(request.user, 'CREATE', 'Customers', f'Bulk upload: {created} customers imported', request)
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        return redirect('customers:customer_list')


class CustomerSampleCSVView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="customer_bulk_upload_sample.csv"'
        writer = csv.writer(response)
        writer.writerow(['name', 'phone', 'company_name', 'city', 'email', 'address', 'opening_balance'])
        writer.writerow(['Ahmed Khan', '03001234567', 'AK Traders', 'Lahore', 'ahmed@example.com', 'Main Bazar, Lahore', '0'])
        writer.writerow(['Sara Agri', '03119876543', 'Sara Farm', 'Multan', '', 'Bypass Road, Multan', '5000'])
        return response
