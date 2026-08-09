from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from apps.seeds.models import Seed, SeedBatch
from .models import StockMovement, StockAdjustment, Warehouse
from .forms import StockAdjustmentForm
from apps.accounts.views import log_activity

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
