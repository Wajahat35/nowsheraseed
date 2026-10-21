from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView, View
from django.urls import reverse_lazy
from django.contrib import messages
from apps.seeds.models import Seed, SeedBatch
from .models import StockMovement, StockAdjustment, Warehouse, SeedProcessing
from .forms import StockAdjustmentForm, SeedProcessingForm
from apps.accounts.views import log_activity
from apps.reports.excel_generator import render_to_excel
from apps.reports.pdf_generator import render_to_pdf

class StockListView(LoginRequiredMixin, ListView):
    model = Seed
    template_name = 'inventory/stock_list.html'
    context_object_name = 'seeds'
    paginate_by = 25

    def get_queryset(self):
        qs = Seed.objects.prefetch_related('batches').all()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q) | qs.filter(variety__icontains=q)
        return qs.order_by('name')

class StockMovementListView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = 'inventory/movement_list.html'
    context_object_name = 'movements'
    paginate_by = 30

    def get_queryset(self):
        qs = StockMovement.objects.select_related('seed', 'batch', 'user').all()
        mtype = self.request.GET.get('mtype')
        if mtype:
            qs = qs.filter(movement_type=mtype)
        return qs

class StockAdjustmentCreateView(LoginRequiredMixin, CreateView):
    model = StockAdjustment
    form_class = StockAdjustmentForm
    template_name = 'inventory/adjustment_form.html'
    success_url = reverse_lazy('inventory:movement_list')

    def form_valid(self, form):
        form.instance.adjusted_by = self.request.user
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATE', 'Inventory', f"Created Stock Adjustment #{self.object.id} for {self.object.seed.name}", self.request)
        messages.success(self.request, "Stock adjustment processed successfully!")
        return response

class InventoryValuationView(LoginRequiredMixin, View):
    template_name = 'inventory/valuation.html'

    def get(self, request):
        seeds = Seed.objects.prefetch_related('batches').all()
        total_valuation = 0
        total_items = 0
        valuation_data = []

        for s in seeds:
            total_qty = s.get_total_stock()
            # Calculate Weighted Average Cost (WAC)
            batches = s.batches.all()
            if batches.exists() and total_qty > 0:
                cost_sum = sum(b.current_qty * b.purchase_price for b in batches)
                wac = cost_sum / total_qty
            else:
                wac = s.purchase_price
            
            item_val = total_qty * wac
            total_valuation += item_val
            total_items += total_qty
            
            valuation_data.append({
                'seed': s,
                'total_qty': total_qty,
                'wac': wac,
                'retail_price': s.retail_price,
                'total_cost_value': item_val,
                'total_retail_value': total_qty * s.retail_price,
            })

        context = {
            'valuation_data': valuation_data,
            'total_valuation': total_valuation,
            'total_items': total_items,
        }
        return render(request, self.template_name, context)

class BatchesBySeedApiView(LoginRequiredMixin, View):
    """Returns JSON list of batches for a given seed pk (for dynamic dropdown filtering)."""
    def get(self, request):
        seed_pk = request.GET.get('seed_id')
        if not seed_pk:
            return JsonResponse({'batches': []})
        batches = SeedBatch.objects.filter(seed_id=seed_pk, current_qty__gt=0).values('id', 'batch_number', 'lot_number', 'current_qty')
        data = list(batches)
        return JsonResponse({'batches': data})


class SeedProcessingListView(LoginRequiredMixin, ListView):
    model = SeedProcessing
    template_name = 'inventory/processing_list.html'
    context_object_name = 'processings'
    paginate_by = 25

    def get_queryset(self):
        qs = SeedProcessing.objects.select_related('grower', 'seed', 'target_batch', 'wastage_type', 'created_by').all()
        q = self.request.GET.get('q')
        seed_id = self.request.GET.get('seed')
        grower_id = self.request.GET.get('grower')

        if q:
            qs = qs.filter(batch_number__icontains=q) | qs.filter(grower__name__icontains=q) | qs.filter(seed__name__icontains=q)
        if seed_id:
            qs = qs.filter(seed_id=seed_id)
        if grower_id:
            qs = qs.filter(grower_id=grower_id)
        return qs.order_by('-date', '-id')

    def get(self, request, *args, **kwargs):
        export_fmt = request.GET.get('export')
        if export_fmt in ('excel', 'pdf'):
            runs = self.get_queryset()
            if export_fmt == 'excel':
                headers = ['Batch #', 'Date', 'Grower', 'Seed Variety', 'Raw Input (KG)', 'Clean Output (KG)', 'Wastage (KG)', 'Recovery %', 'Wastage %', 'Equiv Bags']
                rows = [
                    [
                        r.batch_number,
                        str(r.date),
                        r.grower.name if r.grower else 'N/A',
                        r.seed.name if r.seed else 'N/A',
                        float(r.raw_input_kg),
                        float(r.clean_seed_kg),
                        float(r.wastage_kg),
                        float(r.recovery_rate),
                        float(r.wastage_rate),
                        float(r.equivalent_bags),
                    ]
                    for r in runs
                ]
                return render_to_excel("seed_processing_runs.xlsx", "SeedProcessing", headers, rows)
            elif export_fmt == 'pdf':
                headers = ['Batch #', 'Date', 'Grower', 'Seed', 'Raw KG', 'Clean KG', 'Wastage KG', 'Rec %']
                rows = [
                    [
                        r.batch_number,
                        str(r.date),
                        r.grower.name[:18] if r.grower else 'N/A',
                        r.seed.name[:16] if r.seed else 'N/A',
                        f"{r.raw_input_kg:,.1f}",
                        f"{r.clean_seed_kg:,.1f}",
                        f"{r.wastage_kg:,.1f}",
                        f"{r.recovery_rate}%",
                    ]
                    for r in runs
                ]
                return render_to_pdf("seed_processing_runs.pdf", "Seed Intake & Processing Audit Report", headers, rows)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.suppliers.models import Supplier
        context['seeds'] = Seed.objects.all().order_by('name')
        context['growers'] = Supplier.objects.all().order_by('name')
        context['selected_seed'] = self.request.GET.get('seed', '')
        context['selected_grower'] = self.request.GET.get('grower', '')
        context['q'] = self.request.GET.get('q', '')
        return context


class SeedProcessingCreateView(LoginRequiredMixin, CreateView):
    model = SeedProcessing
    form_class = SeedProcessingForm
    template_name = 'inventory/processing_form.html'
    success_url = reverse_lazy('inventory:processing_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        p = self.object
        log_activity(
            self.request.user, 'CREATE', 'Inventory',
            f"Processed Intake Run {p.batch_number} - Raw: {p.raw_input_kg} KG -> Clean: {p.clean_seed_kg} KG ({p.equivalent_bags} Bags) + Wastage: {p.wastage_kg} KG",
            self.request
        )
        messages.success(
            self.request,
            f"Intake Run {p.batch_number} successfully processed! Added {p.clean_seed_kg:,.1f} KG clean seed (≈ {p.equivalent_bags} Bags) to usable inventory and diverted {p.wastage_kg:,.1f} KG to wastage stock."
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.wastage.models import WastageType
        context['seeds'] = Seed.objects.all().order_by('name')
        context['wastage_types'] = WastageType.objects.all().order_by('name')
        return context


class SeedProcessingDetailView(LoginRequiredMixin, DetailView):
    model = SeedProcessing
    template_name = 'inventory/processing_detail.html'
    context_object_name = 'processing'

