import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View, DeleteView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.utils.dateparse import parse_date

from .models import (
    WastageType, WastageRateHistory, WastageStock,
    WastageMovement, WastageInvoice, WastageInvoiceItem
)
from .forms import WastageTypeForm, WastageRateUpdateForm, WastageInvoiceForm
from apps.accounts.views import log_activity, AdminRequiredMixin
from apps.reports.excel_generator import render_to_excel
from apps.reports.pdf_generator import render_to_pdf


class WastageInventoryView(LoginRequiredMixin, View):
    template_name = 'wastage/inventory.html'

    def get(self, request):
        types = WastageType.objects.prefetch_related('stock', 'rate_history').all().order_by('name')
        
        # Ensure every type has a stock record
        for t in types:
            if not hasattr(t, 'stock'):
                WastageStock.objects.get_or_create(wastage_type=t)

        # Fresh fetch with stock joined
        types = WastageType.objects.prefetch_related('stock', 'rate_history').all().order_by('name')

        total_stock_kg = sum((t.stock.current_stock_kg for t in types if hasattr(t, 'stock')), Decimal('0.00'))
        total_bags_50kg = int(total_stock_kg // Decimal('50.0')) if total_stock_kg > Decimal('0') else 0
        total_loose_kg = total_stock_kg % Decimal('50.0') if total_stock_kg > Decimal('0') else Decimal('0')

        # Recent rate updates audit trail
        rate_logs = WastageRateHistory.objects.select_related('wastage_type', 'changed_by').order_by('-created_at')[:15]

        # Recent stock movements
        recent_movements = WastageMovement.objects.select_related('wastage_type', 'user').order_by('-created_at')[:15]

        context = {
            'wastage_types': types,
            'total_stock_kg': total_stock_kg,
            'total_bags_50kg': total_bags_50kg,
            'total_loose_kg': total_loose_kg,
            'rate_logs': rate_logs,
            'recent_movements': recent_movements,
            'rate_form': WastageRateUpdateForm(),
            'type_form': WastageTypeForm(),
        }
        return render(request, self.template_name, context)


class WastageRateUpdateView(LoginRequiredMixin, View):
    def post(self, request):
        type_id = request.POST.get('wastage_type_id')
        new_rate_val = request.POST.get('new_rate')
        reason = request.POST.get('reason', '')

        try:
            w_type = get_object_or_404(WastageType, pk=type_id)
            new_rate = Decimal(str(new_rate_val))
            old_rate = w_type.price_per_kg

            if new_rate < Decimal('0'):
                messages.error(request, "Rate per KG cannot be negative.")
                return redirect('wastage:wastage_inventory')

            w_type.price_per_kg = new_rate
            w_type.save()

            WastageRateHistory.objects.create(
                wastage_type=w_type,
                old_rate=old_rate,
                new_rate=new_rate,
                changed_by=request.user,
                reason=reason or f"Rate updated from PKR {old_rate} to PKR {new_rate}"
            )

            log_activity(
                request.user, 'UPDATE', 'Wastage',
                f"Updated {w_type.name} price: PKR {old_rate} -> PKR {new_rate}/KG",
                request
            )
            messages.success(request, f"Rate for '{w_type.name}' successfully updated to PKR {new_rate:,.2f} per KG!")
        except Exception as e:
            messages.error(request, f"Error updating rate: {str(e)}")

        return redirect('wastage:wastage_inventory')


class WastageTypeCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = WastageTypeForm(request.POST)
        if form.is_valid():
            w_type = form.save()
            WastageStock.objects.get_or_create(wastage_type=w_type)
            log_activity(request.user, 'CREATE', 'Wastage', f"Created Wastage Grade '{w_type.name}'", request)
            messages.success(request, f"Wastage Grade '{w_type.name}' registered successfully!")
        else:
            messages.error(request, "Could not add wastage grade. Please ensure the name is unique.")
        return redirect('wastage:wastage_inventory')


class WastageInvoiceListView(LoginRequiredMixin, ListView):
    model = WastageInvoice
    template_name = 'wastage/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 25

    def get_queryset(self):
        qs = WastageInvoice.objects.prefetch_related('items__wastage_type').all()
        q = self.request.GET.get('q')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        pstatus = self.request.GET.get('pstatus')

        if q:
            qs = qs.filter(
                Q(invoice_number__icontains=q) |
                Q(buyer_name__icontains=q) |
                Q(buyer_phone__icontains=q) |
                Q(reference_no__icontains=q)
            )
        if start_date:
            s_d = parse_date(start_date)
            if s_d:
                qs = qs.filter(date__gte=s_d)
        if end_date:
            e_d = parse_date(end_date)
            if e_d:
                qs = qs.filter(date__lte=e_d)
        if pstatus:
            qs = qs.filter(payment_status=pstatus)

        return qs.order_by('-date', '-id')

    def get(self, request, *args, **kwargs):
        export_fmt = request.GET.get('export')
        if export_fmt in ('excel', 'pdf'):
            invoices = self.get_queryset()
            if export_fmt == 'excel':
                headers = ['Invoice #', 'Date', 'Buyer Name', 'Contact', 'Total KG Sold', 'Grand Total (PKR)', 'Paid (PKR)', 'Balance (PKR)', 'Status']
                rows = [
                    [
                        inv.invoice_number,
                        str(inv.date),
                        inv.buyer_name,
                        inv.buyer_phone or '-',
                        float(inv.total_weight_kg),
                        float(inv.grand_total),
                        float(inv.paid_amount),
                        float(inv.due_amount),
                        inv.payment_status
                    ]
                    for inv in invoices
                ]
                return render_to_excel("wastage_sales_invoices.xlsx", "WastageSales", headers, rows)
            elif export_fmt == 'pdf':
                headers = ['Invoice #', 'Date', 'Buyer', 'KG Sold', 'Grand Total', 'Paid', 'Status']
                rows = [
                    [
                        inv.invoice_number,
                        str(inv.date),
                        inv.buyer_name[:18],
                        f"{inv.total_weight_kg:,.1f} KG",
                        f"PKR {inv.grand_total:,.0f}",
                        f"PKR {inv.paid_amount:,.0f}",
                        inv.payment_status
                    ]
                    for inv in invoices
                ]
                return render_to_pdf("wastage_sales_invoices.pdf", "Wastage Sales & Dispatch Report", headers, rows)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['pstatus'] = self.request.GET.get('pstatus', '')

        # KPI aggregations
        totals = WastageInvoice.objects.aggregate(
            total_rev=Sum('grand_total'),
            total_paid=Sum('paid_amount'),
        )
        context['kpi_total_revenue'] = totals['total_rev'] or Decimal('0.00')
        context['kpi_total_paid'] = totals['total_paid'] or Decimal('0.00')
        context['kpi_receivables'] = max(Decimal('0.00'), context['kpi_total_revenue'] - context['kpi_total_paid'])
        return context


class WastageInvoiceCreateView(LoginRequiredMixin, View):
    template_name = 'wastage/invoice_form.html'

    def get(self, request):
        form = WastageInvoiceForm()
        types = WastageType.objects.prefetch_related('stock').all().order_by('name')
        return render(request, self.template_name, {
            'form': form,
            'wastage_types': types,
        })

    def post(self, request):
        form = WastageInvoiceForm(request.POST)
        items_data = request.POST.get('items_data')

        if form.is_valid() and items_data:
            try:
                items_list = json.loads(items_data)
                if not items_list:
                    messages.error(request, "Please add at least one wastage item to invoice.")
                    return redirect('wastage:invoice_create')

                with transaction.atomic():
                    # 1. Check stock availability for all items
                    for it in items_list:
                        type_id = it.get('wastage_type_id')
                        qty_kg = Decimal(str(it.get('quantity_kg', 0)))
                        w_type = WastageType.objects.get(id=type_id)
                        stock, _ = WastageStock.objects.get_or_create(wastage_type=w_type)

                        if qty_kg > Decimal(str(stock.current_stock_kg)):
                            messages.error(
                                request,
                                f"Cannot sell {qty_kg:,.1f} KG of '{w_type.name}'. Available stock is only {stock.current_stock_kg:,.1f} KG."
                            )
                            return redirect('wastage:invoice_create')

                    # 2. Save Invoice
                    invoice = form.save(commit=False)
                    invoice.created_by = request.user
                    invoice.save()

                    subtotal = Decimal('0.00')
                    for it in items_list:
                        type_id = it.get('wastage_type_id')
                        qty_kg = Decimal(str(it.get('quantity_kg', 0)))
                        rate_kg = Decimal(str(it.get('rate_per_kg', 0)))
                        w_type = WastageType.objects.get(id=type_id)

                        item_sub = qty_kg * rate_kg
                        subtotal += item_sub

                        WastageInvoiceItem.objects.create(
                            invoice=invoice,
                            wastage_type=w_type,
                            quantity_kg=qty_kg,
                            rate_per_kg=rate_kg,
                            subtotal=item_sub
                        )

                    invoice.subtotal = subtotal
                    invoice.grand_total = max(Decimal('0'), subtotal - (invoice.discount_amount or Decimal('0')))
                    invoice.save()

                    log_activity(
                        request.user, 'CREATE', 'Wastage',
                        f"Generated Wastage Invoice {invoice.invoice_number} for {invoice.buyer_name} (PKR {invoice.grand_total:,.2f})",
                        request
                    )
                    messages.success(request, f"Wastage Invoice {invoice.invoice_number} created successfully!")
                    return redirect('wastage:invoice_detail', pk=invoice.pk)

            except Exception as e:
                messages.error(request, f"Error saving invoice: {str(e)}")

        return redirect('wastage:invoice_create')


class WastageInvoiceDetailView(LoginRequiredMixin, DetailView):
    model = WastageInvoice
    template_name = 'wastage/invoice_detail.html'
    context_object_name = 'invoice'


class WastageInvoiceDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = WastageInvoice
    success_url = reverse_lazy('wastage:invoice_list')

    def form_valid(self, form):
        invoice = self.get_object()
        inv_num = invoice.invoice_number
        with transaction.atomic():
            # Restore stock for each wastage item
            for item in invoice.items.all():
                stock, _ = WastageStock.objects.get_or_create(wastage_type=item.wastage_type)
                stock.current_stock_kg = Decimal(str(stock.current_stock_kg)) + item.quantity_kg
                stock.save()

                WastageMovement.objects.create(
                    movement_type='RETURN',
                    wastage_type=item.wastage_type,
                    quantity_kg=item.quantity_kg,
                    reference_no=inv_num,
                    notes=f"Stock restored from deleted Wastage Invoice {inv_num}",
                    user=self.request.user
                )

            log_activity(self.request.user, 'DELETE', 'Wastage', f"Deleted Wastage Invoice {inv_num} and restored stock", self.request)
            messages.success(self.request, f"Wastage Invoice {inv_num} deleted and stock restored successfully.")
            return super().form_valid(form)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.form_valid(self.get_form())
