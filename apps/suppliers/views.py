from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views import View
from django.http import HttpResponse
import csv, io
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Supplier
from .forms import SupplierForm
from apps.accounts.views import log_activity

class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'suppliers/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 20

    def get_queryset(self):
        qs = Supplier.objects.all()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q) | qs.filter(phone__icontains=q) | qs.filter(company_name__icontains=q)
        return qs.order_by('-id')

class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html'
    success_url = reverse_lazy('suppliers:supplier_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATE', 'Suppliers', f"Created supplier {self.object.name} ({self.object.code})", self.request)
        messages.success(self.request, f"Supplier {self.object.name} added successfully!")
        return response

class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'suppliers/supplier_form.html'
    success_url = reverse_lazy('suppliers:supplier_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'UPDATE', 'Suppliers', f"Updated supplier {self.object.name} ({self.object.code})", self.request)
        messages.success(self.request, f"Supplier {self.object.name} updated successfully!")
        return response

class SupplierDeleteView(LoginRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'suppliers/supplier_confirm_delete.html'
    success_url = reverse_lazy('suppliers:supplier_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_activity(request.user, 'DELETE', 'Suppliers', f"Deleted supplier {obj.name} ({obj.code})", request)
        messages.success(request, f"Supplier {obj.name} deleted.")
        return super().delete(request, *args, **kwargs)

class SupplierLedgerView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = 'suppliers/supplier_ledger.html'
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.purchases.models import PurchaseInvoice
        supplier = self.object
        invoices = PurchaseInvoice.objects.filter(supplier=supplier).order_by('date')
        
        ledger_entries = []
        running_balance = supplier.opening_balance
        
        if supplier.opening_balance != 0:
            ledger_entries.append({
                'date': supplier.created_at,
                'reference': 'OPENING BALANCE',
                'description': 'Supplier Opening Balance',
                'debit': 0,
                'credit': supplier.opening_balance,
                'balance': running_balance
            })
            
        for inv in invoices:
            running_balance += inv.grand_total
            ledger_entries.append({
                'date': inv.date,
                'reference': inv.invoice_number,
                'description': 'Purchase Invoice / Bill',
                'debit': 0,
                'credit': inv.grand_total,
                'balance': running_balance,
            })
            if inv.paid_amount > 0:
                running_balance -= inv.paid_amount
                ledger_entries.append({
                    'date': inv.date,
                    'reference': f"PAY-{inv.invoice_number}",
                    'description': f"Payment Paid ({inv.payment_method})",
                    'debit': inv.paid_amount,
                    'credit': 0,
                    'balance': running_balance
                })

        context['ledger_entries'] = ledger_entries
        context['current_balance'] = running_balance
        return context


class SupplierBulkUploadView(LoginRequiredMixin, View):
    template_name = 'suppliers/supplier_bulk_upload.html'

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
                _, was_created = Supplier.objects.get_or_create(
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
            messages.success(request, f'Upload complete: {created} suppliers created, {skipped} skipped/duplicates.')
            log_activity(request.user, 'CREATE', 'Suppliers', f'Bulk upload: {created} suppliers imported', request)
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        return redirect('suppliers:supplier_list')


class SupplierSampleCSVView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="supplier_bulk_upload_sample.csv"'
        writer = csv.writer(response)
        writer.writerow(['name', 'phone', 'company_name', 'city', 'email', 'address', 'opening_balance'])
        writer.writerow(['Ali Suppliers', '03001234567', 'Ali Agri Co', 'Lahore', 'ali@example.com', 'Grain Market, Lahore', '0'])
        return response
