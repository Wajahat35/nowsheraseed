import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from .models import PurchaseInvoice, PurchaseItem
from .forms import PurchaseInvoiceForm
from apps.seeds.models import Seed, SeedBatch
from apps.suppliers.models import Supplier
from apps.accounts.views import log_activity


class PurchaseListView(LoginRequiredMixin, ListView):
    model = PurchaseInvoice
    template_name = 'purchases/purchase_list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        qs = PurchaseInvoice.objects.select_related('supplier').all()
        q = self.request.GET.get('q')
        pstatus = self.request.GET.get('pstatus')
        if q:
            qs = qs.filter(invoice_number__icontains=q) | qs.filter(supplier__name__icontains=q) | qs.filter(supplier_bill_no__icontains=q)
        if pstatus:
            qs = qs.filter(payment_status=pstatus)
        return qs.order_by('-id')


class PurchaseCreateView(LoginRequiredMixin, View):
    template_name = 'purchases/purchase_form.html'

    def get(self, request):
        form = PurchaseInvoiceForm()
        suppliers = Supplier.objects.filter(is_active=True)
        seeds = Seed.objects.filter(status='Active').prefetch_related('batches')
        return render(request, self.template_name, {
            'form': form,
            'suppliers': suppliers,
            'seeds': seeds,
        })

    def post(self, request):
        form = PurchaseInvoiceForm(request.POST)
        items_data = request.POST.get('items_data')

        if form.is_valid() and items_data:
            try:
                items_list = json.loads(items_data)
                if not items_list:
                    messages.error(request, "Please add at least one item to the purchase invoice.")
                    return redirect('purchases:purchase_create')

                with transaction.atomic():
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
                        tax_rate = Decimal(str(item.get('tax_rate', 0)))

                        seed = Seed.objects.get(id=seed_id)
                        batch = SeedBatch.objects.get(id=batch_id) if batch_id else None

                        item_subtotal = qty * price
                        tax_amount = item_subtotal * (tax_rate / Decimal('100'))

                        subtotal += item_subtotal
                        tax_total += tax_amount

                        PurchaseItem.objects.create(
                            purchase_invoice=invoice,
                            seed=seed,
                            batch=batch,
                            quantity=qty,
                            unit_price=price,
                            tax_rate=tax_rate,
                            subtotal=item_subtotal + tax_amount
                        )

                    invoice.subtotal = subtotal
                    invoice.tax_amount = tax_total
                    invoice.grand_total = (subtotal + tax_total) - (invoice.discount_amount or Decimal('0'))
                    invoice.save()

                    log_activity(request.user, 'CREATE', 'Purchases', f"Created Purchase Bill {invoice.invoice_number} (PKR {invoice.grand_total})", request)
                    messages.success(request, f"Purchase Bill {invoice.invoice_number} created successfully!")
                    return redirect('purchases:purchase_detail', pk=invoice.pk)

            except Exception as e:
                messages.error(request, f"Error saving purchase invoice: {str(e)}")

        return redirect('purchases:purchase_create')


class PurchaseDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseInvoice
    template_name = 'purchases/purchase_detail.html'
    context_object_name = 'invoice'


class PurchasePrintView(LoginRequiredMixin, DetailView):
    model = PurchaseInvoice
    template_name = 'purchases/purchase_print.html'
    context_object_name = 'invoice'


class RecordPurchasePaymentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(PurchaseInvoice, pk=pk)
        try:
            amount_val = request.POST.get('amount', '0')
            amount = Decimal(str(amount_val))
            payment_method = request.POST.get('payment_method', 'Cash')
            ref_no = request.POST.get('reference_no', '')

            if amount <= Decimal('0'):
                messages.error(request, "Payment amount must be greater than 0.")
                return redirect('purchases:purchase_detail', pk=invoice.pk)

            invoice.paid_amount = Decimal(str(invoice.paid_amount or 0)) + amount
            invoice.save()

            # Record Double-Entry Journal Voucher
            try:
                from apps.finance.models import JournalVoucher, JournalItem, ChartOfAccount
                account_code = '1000' if payment_method == 'Cash' else '1010'
                cash_account = ChartOfAccount.objects.filter(code=account_code).first()
                ap_account = ChartOfAccount.objects.filter(code='2000').first()

                if cash_account and ap_account:
                    voucher = JournalVoucher.objects.create(
                        voucher_type='PAYMENT',
                        description=f"Payment Sent PKR {amount:,.2f} for Purchase Bill {invoice.invoice_number} ({invoice.supplier.name})",
                        reference_no=ref_no or invoice.invoice_number,
                        created_by=request.user
                    )
                    JournalItem.objects.create(
                        voucher=voucher,
                        account=ap_account,
                        debit=amount,
                        credit=0,
                        narration=f"Payable settled for {invoice.supplier.name}"
                    )
                    JournalItem.objects.create(
                        voucher=voucher,
                        account=cash_account,
                        debit=0,
                        credit=amount,
                        narration=f"Cash/Bank paid for {invoice.invoice_number}"
                    )
            except Exception:
                pass

            log_activity(request.user, 'UPDATE', 'Purchases', f"Recorded payment PKR {amount} for Purchase Bill {invoice.invoice_number}", request)
            messages.success(request, f"Payment of PKR {amount:,.2f} recorded! Bill status: {invoice.payment_status}")

        except Exception as e:
            messages.error(request, f"Error recording payment: {str(e)}")

        return redirect('purchases:purchase_detail', pk=invoice.pk)
