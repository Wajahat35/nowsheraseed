from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView, UpdateView, View
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.utils.dateparse import parse_date
from .models import GatePass
from .forms import GatePassForm
from apps.sales.models import SalesInvoice
from apps.purchases.models import PurchaseInvoice
from apps.accounts.views import log_activity

class GatePassListView(LoginRequiredMixin, ListView):
    model = GatePass
    template_name = 'gatepass/gatepass_list.html'
    context_object_name = 'gatepasses'
    paginate_by = 30

    def get_queryset(self):
        qs = GatePass.objects.all()
        q = self.request.GET.get('q')
        ptype = self.request.GET.get('ptype')
        if q:
            qs = qs.filter(pass_number__icontains=q) | qs.filter(vehicle_number__icontains=q) | qs.filter(driver_name__icontains=q) | qs.filter(invoice_reference__icontains=q)
        if ptype:
            qs = qs.filter(pass_type=ptype)
        return qs.order_by('-id')

class GatePassCreateView(LoginRequiredMixin, CreateView):
    model = GatePass
    form_class = GatePassForm
    template_name = 'gatepass/gatepass_form.html'
    success_url = reverse_lazy('gatepass:gatepass_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if not form.instance.status:
            form.instance.status = 'Issued'
        self.object = form.save()
        log_activity(self.request.user, 'CREATE', 'GatePass', f"Created Gate Pass {self.object.pass_number} for Vehicle {self.object.vehicle_number}", self.request)
        if self.object.is_stock_updated:
            messages.success(self.request, f"Gate Pass {self.object.pass_number} issued & stock automatically inwarded to inventory!")
        else:
            messages.success(self.request, f"Gate Pass {self.object.pass_number} issued successfully!")
        return redirect('gatepass:gatepass_detail', pk=self.object.pk)

class GatePassDetailView(LoginRequiredMixin, DetailView):
    model = GatePass
    template_name = 'gatepass/gatepass_detail.html'
    context_object_name = 'gatepass'

class GatePassPrintView(LoginRequiredMixin, DetailView):
    model = GatePass
    template_name = 'gatepass/gatepass_print.html'
    context_object_name = 'gatepass'

class GatePassVerifyView(LoginRequiredMixin, DetailView):
    model = GatePass
    template_name = 'gatepass/gatepass_verify.html'
    context_object_name = 'gatepass'

    def post(self, request, *args, **kwargs):
        gatepass = self.get_object()
        gatepass.status = 'Verified'
        gatepass.verified_by = request.user
        gatepass.save()
        gatepass.process_inward_stock(request.user)
        log_activity(request.user, 'UPDATE', 'GatePass', f"Verified Gate Pass {gatepass.pass_number}", request)
        messages.success(request, f"Gate Pass {gatepass.pass_number} security verified & inward stock confirmed!")
        return redirect('gatepass:gatepass_detail', pk=gatepass.pk)

class InwardStockActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        gatepass = get_object_or_404(GatePass, pk=pk)
        success = gatepass.process_inward_stock(request.user)
        if success:
            messages.success(request, f"Stock successfully inwarded into inventory for Gate Pass {gatepass.pass_number}!")
        else:
            if gatepass.is_stock_updated:
                messages.info(request, f"Stock for Gate Pass {gatepass.pass_number} was already inwarded.")
            else:
                messages.warning(request, "Unable to inward stock: Please ensure invoice reference (PUR-XXXX) or seed & quantity is provided.")
        return redirect('gatepass:gatepass_detail', pk=pk)

class InvoiceDetailsApiView(LoginRequiredMixin, View):
    def get(self, request):
        ref = request.GET.get('ref')
        if not ref:
            return JsonResponse({'success': False, 'message': 'Reference missing'})
            
        if ref.startswith('INV-'):
            inv = SalesInvoice.objects.filter(invoice_number=ref).first()
            if inv:
                bags = sum(item.quantity for item in inv.items.all())
                weight_kg = float(sum(item.quantity * item.seed.weight_kg for item in inv.items.all()))
                return JsonResponse({'success': True, 'bags': bags, 'weight_kg': weight_kg, 'type': 'SALES'})
                
        elif ref.startswith('PUR-'):
            pur = PurchaseInvoice.objects.filter(invoice_number=ref).first()
            if pur:
                bags = sum(item.quantity for item in pur.items.all())
                weight_kg = float(sum(item.quantity * item.seed.weight_kg for item in pur.items.all()))
                return JsonResponse({'success': True, 'bags': bags, 'weight_kg': weight_kg, 'type': 'PURCHASE'})

        return JsonResponse({'success': False, 'message': 'Invoice not found'})

class GatePassReportView(LoginRequiredMixin, View):
    template_name = 'gatepass/gatepass_report.html'

    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        pass_type = request.GET.get('pass_type')

        qs = GatePass.objects.all()

        if start_date:
            s_date = parse_date(start_date)
            if s_date:
                qs = qs.filter(date_time__date__gte=s_date)

        if end_date:
            e_date = parse_date(end_date)
            if e_date:
                qs = qs.filter(date_time__date__lte=e_date)

        if pass_type:
            qs = qs.filter(pass_type=pass_type)

        gatepasses = qs.order_by('-id')

        # Export handlers
        export_fmt = request.GET.get('export')
        if export_fmt == 'pdf':
            from apps.reports.pdf_generator import render_to_pdf
            headers = ["Pass #", "Type", "Date/Time", "Vehicle #", "Driver Name", "CNIC", "Bags", "Weight (Kg)", "Ref #"]
            rows = []
            for gp in gatepasses:
                rows.append([
                    gp.pass_number,
                    gp.get_pass_type_display(),
                    gp.date_time.strftime("%Y-%m-%d %H:%M"),
                    gp.vehicle_number,
                    gp.driver_name,
                    gp.driver_cnic,
                    str(gp.total_bags),
                    str(gp.total_weight_kg),
                    gp.invoice_reference or "-"
                ])
            return render_to_pdf("gate_pass_report.pdf", "Gate Pass Logistics Report", headers, rows)
            
        elif export_fmt == 'excel':
            from apps.reports.excel_generator import render_to_excel
            headers = ["Pass #", "Type", "Date/Time", "Vehicle #", "Driver Name", "CNIC", "Driver Mobile", "Transport", "Bags", "Weight (Kg)", "Ref #", "Status"]
            rows = []
            for gp in gatepasses:
                rows.append([
                    gp.pass_number,
                    gp.get_pass_type_display(),
                    gp.date_time.strftime("%Y-%m-%d %H:%M"),
                    gp.vehicle_number,
                    gp.driver_name,
                    gp.driver_cnic,
                    gp.driver_mobile,
                    gp.transport_company or "-",
                    gp.total_bags,
                    float(gp.total_weight_kg),
                    gp.invoice_reference or "-",
                    gp.status
                ])
            return render_to_excel("gate_pass_report.xlsx", "GatePassLogistics", headers, rows)

        return render(request, self.template_name, {
            'gatepasses': gatepasses,
            'start_date': start_date,
            'end_date': end_date,
            'pass_type': pass_type
        })
