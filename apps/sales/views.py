import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date
from .models import SalesInvoice, SalesItem, Quotation, QuotationItem
from .forms import SalesInvoiceForm, QuotationForm
from apps.seeds.models import Seed, SeedBatch
from apps.customers.models import Customer
from apps.accounts.views import log_activity
from apps.reports.pdf_generator import render_to_pdf
from apps.reports.excel_generator import render_to_excel

class SalesListView(LoginRequiredMixin, ListView):
    model = SalesInvoice
    template_name = 'sales/sales_list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        qs = SalesInvoice.objects.select_related('customer').all()
        q = self.request.GET.get('q')
        customer_id = self.request.GET.get('customer')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        stype = self.request.GET.get('stype')
        pstatus = self.request.GET.get('pstatus')

        if q:
            qs = qs.filter(
                Q(invoice_number__icontains=q) |
                Q(customer__name__icontains=q) |
                Q(customer__company_name__icontains=q) |
                Q(customer__phone__icontains=q)
            )
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if start_date:
            s_date = parse_date(start_date)
            if s_date:
                qs = qs.filter(date__gte=s_date)
        if end_date:
            e_date = parse_date(end_date)
            if e_date:
                qs = qs.filter(date__lte=e_date)
        if stype:
            qs = qs.filter(sales_type=stype)
        if pstatus:
            qs = qs.filter(payment_status=pstatus)

        return qs.order_by('-date', '-id')

    def get(self, request, *args, **kwargs):
        export_fmt = request.GET.get('export')
        if export_fmt in ('excel', 'pdf'):
            invoices = self.get_queryset()
            if export_fmt == 'excel':
                headers = ['Invoice #', 'Customer', 'Date', 'Type', 'Grand Total (PKR)', 'Paid (PKR)', 'Balance (PKR)', 'Payment Method', 'Status']
                rows = [
                    [
                        inv.invoice_number,
                        inv.customer.name if inv.customer else 'N/A',
                        str(inv.date),
                        inv.get_sales_type_display(),
                        float(inv.grand_total),
                        float(inv.paid_amount),
                        float(inv.due_amount),
                        inv.payment_method,
                        inv.payment_status
                    ]
                    for inv in invoices
                ]
                return render_to_excel("sales_invoices.xlsx", "SalesInvoices", headers, rows)
            elif export_fmt == 'pdf':
                headers = ['Invoice #', 'Customer', 'Date', 'Type', 'Grand Total', 'Paid', 'Status']
                rows = [
                    [
                        inv.invoice_number,
                        (inv.customer.name[:22] if inv.customer else 'N/A'),
                        str(inv.date),
                        inv.sales_type,
                        f"PKR {inv.grand_total:,.0f}",
                        f"PKR {inv.paid_amount:,.0f}",
                        inv.payment_status
                    ]
                    for inv in invoices
                ]
                return render_to_pdf("sales_invoices.pdf", "Sales Invoices Report", headers, rows)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all().order_by('name')
        context['selected_customer'] = self.request.GET.get('customer', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['stype'] = self.request.GET.get('stype', '')
        context['pstatus'] = self.request.GET.get('pstatus', '')
        context['q'] = self.request.GET.get('q', '')
        return context

class SalesCreateView(LoginRequiredMixin, View):
    template_name = 'sales/sales_form.html'

    def get(self, request):
        form = SalesInvoiceForm()
        customers = Customer.objects.filter(is_active=True)
        seeds = Seed.objects.filter(status='Active').prefetch_related('batches')
        return render(request, self.template_name, {
            'form': form,
            'customers': customers,
            'seeds': seeds,
        })

    def post(self, request):
        form = SalesInvoiceForm(request.POST)
        items_data = request.POST.get('items_data')  # JSON payload of cart items

        if form.is_valid() and items_data:
            try:
                items_list = json.loads(items_data)
                if not items_list:
                    messages.error(request, "Cart is empty. Please add items before saving invoice.")
                    return redirect('sales:sales_create')

                with transaction.atomic():
                    # 1. Validate all cart items against available stock before saving
                    for item in items_list:
                        seed_id = item.get('seed_id')
                        batch_id = item.get('batch_id')
                        qty = int(item.get('quantity', 1))

                        seed = Seed.objects.get(id=seed_id)
                        batch = SeedBatch.objects.get(id=batch_id) if batch_id else None

                        if batch:
                            available_stock = batch.current_qty
                            stock_label = f"Batch #{batch.batch_number} ({seed.name})"
                        else:
                            available_stock = seed.get_total_stock()
                            stock_label = f"Seed '{seed.name}'"

                        if qty > available_stock:
                            messages.error(
                                request,
                                f"Cannot generate Sales Invoice: Requested quantity ({qty} Bags) exceeds available stock for {stock_label} ({available_stock} Bags available)."
                            )
                            return redirect('sales:sales_create')

                    invoice = form.save(commit=False)
                    invoice.created_by = request.user
                    invoice.save()

                    subtotal = Decimal('0')
                    tax_total = Decimal('0')

                    for item in items_list:
                        seed_id = item.get('seed_id')
                        batch_id = item.get('batch_id')
                        qty = int(item.get('quantity', 1))
                        price = Decimal(str(item.get('unit_price', 0)))
                        discount = Decimal(str(item.get('discount', 0)))
                        tax_rate = Decimal(str(item.get('tax_rate', 0)))

                        seed = Seed.objects.get(id=seed_id)
                        batch = SeedBatch.objects.get(id=batch_id) if batch_id else None

                        item_subtotal = (price - discount) * qty
                        tax_amount = item_subtotal * (tax_rate / Decimal('100'))

                        subtotal += item_subtotal
                        tax_total += tax_amount

                        SalesItem.objects.create(
                            sales_invoice=invoice,
                            seed=seed,
                            batch=batch,
                            quantity=qty,
                            unit_price=price,
                            discount=discount,
                            tax_rate=tax_rate,
                            subtotal=item_subtotal + tax_amount
                        )

                    invoice.subtotal = subtotal
                    invoice.tax_amount = tax_total
                    invoice.grand_total = (subtotal + tax_total) - (invoice.discount_amount or Decimal('0'))
                    invoice.save()

                    log_activity(request.user, 'CREATE', 'Sales', f"Created Sales Invoice {invoice.invoice_number} for {invoice.customer.name} (PKR {invoice.grand_total})", request)
                    messages.success(request, f"Sales Invoice {invoice.invoice_number} created successfully!")
                    return redirect('sales:sales_detail', pk=invoice.pk)

            except Exception as e:
                messages.error(request, f"Error creating invoice: {str(e)}")

        return redirect('sales:sales_create')

class SalesDetailView(LoginRequiredMixin, DetailView):
    model = SalesInvoice
    template_name = 'sales/sales_detail.html'
    context_object_name = 'invoice'

class SalesPrintInvoiceView(LoginRequiredMixin, DetailView):
    model = SalesInvoice
    template_name = 'sales/invoice_print.html'
    context_object_name = 'invoice'

class RegenerateQRView(LoginRequiredMixin, View):
    """Regenerate QR code for an invoice and redirect back."""
    def get(self, request, pk):
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        invoice._regenerate_qr()
        SalesInvoice.objects.filter(pk=pk).update(qr_code=invoice.qr_code)
        messages.success(request, f"QR Code regenerated for {invoice.invoice_number}!")
        return redirect('sales:sales_detail', pk=pk)

class InvoiceQRVerifyView(View):
    """Public QR scan verification page — no login required."""
    def get(self, request, invoice_number):
        invoice = get_object_or_404(SalesInvoice, invoice_number=invoice_number)
        from apps.settings_app.models import CompanyProfile
        company = CompanyProfile.get_instance()
        return render(request, 'sales/invoice_qr_verify.html', {'invoice': invoice, 'company': company})

class RecordPaymentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        try:
            amount_val = request.POST.get('amount', '0')
            amount = Decimal(str(amount_val))
            payment_method = request.POST.get('payment_method', 'Cash')
            ref_no = request.POST.get('reference_no', '')
            notes = request.POST.get('notes', '')

            if amount <= Decimal('0'):
                messages.error(request, "Payment amount must be greater than 0.")
                return redirect('sales:sales_detail', pk=invoice.pk)

            invoice.paid_amount = Decimal(str(invoice.paid_amount or 0)) + amount
            invoice.save()

            # Record Double-Entry Journal Voucher
            try:
                from apps.finance.models import JournalVoucher, JournalItem, ChartOfAccount
                account_code = '1000' if payment_method == 'Cash' else '1010'
                cash_account = ChartOfAccount.objects.filter(code=account_code).first()
                ar_account = ChartOfAccount.objects.filter(code='1100').first()

                if cash_account and ar_account:
                    voucher = JournalVoucher.objects.create(
                        voucher_type='RECEIPT',
                        description=f"Payment Received PKR {amount:,.2f} for Invoice {invoice.invoice_number} ({invoice.customer.name})",
                        reference_no=ref_no or invoice.invoice_number,
                        created_by=request.user
                    )
                    JournalItem.objects.create(
                        voucher=voucher,
                        account=cash_account,
                        debit=amount,
                        credit=0,
                        narration=f"Payment received for invoice {invoice.invoice_number}"
                    )
                    JournalItem.objects.create(
                        voucher=voucher,
                        account=ar_account,
                        debit=0,
                        credit=amount,
                        narration=f"Receivable balance update for {invoice.customer.name}"
                    )
            except Exception:
                pass

            log_activity(request.user, 'UPDATE', 'Sales', f"Recorded payment PKR {amount} for Invoice {invoice.invoice_number}", request)
            messages.success(request, f"Payment of PKR {amount:,.2f} recorded successfully for Invoice {invoice.invoice_number}! Invoice status: {invoice.payment_status}")

        except Exception as e:
            messages.error(request, f"Error recording payment: {str(e)}")

        return redirect('sales:sales_detail', pk=invoice.pk)

class PosTerminalView(LoginRequiredMixin, View):
    template_name = 'sales/pos.html'

    def get(self, request):
        customers = Customer.objects.filter(is_active=True)
        seeds = Seed.objects.filter(status='Active').prefetch_related('batches')
        return render(request, self.template_name, {
            'customers': customers,
            'seeds': seeds,
        })

class QuotationListView(LoginRequiredMixin, ListView):
    model = Quotation
    template_name = 'sales/quotation_list.html'
    context_object_name = 'quotations'
    paginate_by = 20
