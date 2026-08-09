from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views import View
from django.http import HttpResponse
import csv, io
from django.urls import reverse_lazy
from django.contrib import messages
from .models import CropType, SeedCategory, Brand, Seed, SeedBatch
from .forms import CropTypeForm, SeedCategoryForm, BrandForm, SeedForm, SeedBatchForm
from apps.accounts.views import log_activity

class SeedListView(LoginRequiredMixin, ListView):
    model = Seed
    template_name = 'seeds/seed_list.html'
    context_object_name = 'seeds'
    paginate_by = 20

    def get_queryset(self):
        qs = Seed.objects.select_related('crop_type', 'category', 'brand').prefetch_related('batches').all()
        q = self.request.GET.get('q')
        crop = self.request.GET.get('crop')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q) | qs.filter(variety__icontains=q) | qs.filter(barcode__icontains=q)
        if crop:
            qs = qs.filter(crop_type_id=crop)
        return qs.order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['crop_types'] = CropType.objects.all()
        context['categories'] = SeedCategory.objects.all()
        context['brands'] = Brand.objects.all()
        return context

class SeedCreateView(LoginRequiredMixin, CreateView):
    model = Seed
    form_class = SeedForm
    template_name = 'seeds/seed_form.html'
    success_url = reverse_lazy('seeds:seed_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATE', 'Seeds', f"Added seed item {self.object.name} ({self.object.code})", self.request)
        messages.success(self.request, f"Seed item {self.object.name} added successfully!")
        return response

class SeedUpdateView(LoginRequiredMixin, UpdateView):
    model = Seed
    form_class = SeedForm
    template_name = 'seeds/seed_form.html'
    success_url = reverse_lazy('seeds:seed_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'UPDATE', 'Seeds', f"Updated seed item {self.object.name} ({self.object.code})", self.request)
        messages.success(self.request, f"Seed item {self.object.name} updated successfully!")
        return response

class SeedDeleteView(LoginRequiredMixin, DeleteView):
    model = Seed
    template_name = 'seeds/seed_confirm_delete.html'
    success_url = reverse_lazy('seeds:seed_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_activity(request.user, 'DELETE', 'Seeds', f"Deleted seed item {obj.name} ({obj.code})", request)
        messages.success(request, f"Seed item {obj.name} deleted.")
        return super().delete(request, *args, **kwargs)

# Crop Type Views
class CropTypeListView(LoginRequiredMixin, ListView):
    model = CropType
    template_name = 'seeds/crop_list.html'
    context_object_name = 'crops'

    def post(self, request):
        form = CropTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Crop Type added successfully!")
            return redirect('seeds:crop_list')
        return self.get(request)

# Category Views
class SeedCategoryListView(LoginRequiredMixin, ListView):
    model = SeedCategory
    template_name = 'seeds/category_list.html'
    context_object_name = 'categories'

    def post(self, request):
        form = SeedCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully!")
            return redirect('seeds:category_list')
        return self.get(request)

# Brand Views
class BrandListView(LoginRequiredMixin, ListView):
    model = Brand
    template_name = 'seeds/brand_list.html'
    context_object_name = 'brands'

    def post(self, request):
        form = BrandForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Brand added successfully!")
            return redirect('seeds:brand_list')
        return self.get(request)

# Batch Management
class SeedBatchListView(LoginRequiredMixin, ListView):
    model = SeedBatch
    template_name = 'seeds/batch_list.html'
    context_object_name = 'batches'
    paginate_by = 25

class SeedBatchCreateView(LoginRequiredMixin, CreateView):
    model = SeedBatch
    form_class = SeedBatchForm
    template_name = 'seeds/batch_form.html'
    success_url = reverse_lazy('seeds:batch_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, 'CREATE', 'Seeds', f"Created Batch #{self.object.batch_number} for {self.object.seed.name}", self.request)
        messages.success(self.request, f"Batch #{self.object.batch_number} added successfully!")
        return response

class BarcodePrintView(LoginRequiredMixin, DetailView):
    model = Seed
    template_name = 'seeds/barcode_print.html'
    context_object_name = 'seed'

class SeedBulkUploadView(LoginRequiredMixin, View):
    template_name = 'seeds/seed_bulk_upload.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please select a CSV file.')
            return render(request, self.template_name)
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Only CSV files are allowed.')
            return render(request, self.template_name)

        try:
            decoded = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
            created = 0
            skipped = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    name = row.get('name', '').strip()
                    variety = row.get('variety', '').strip()
                    if not name or not variety:
                        errors.append(f'Row {row_num}: name and variety are required.')
                        skipped += 1
                        continue

                    packing_size = row.get('packing_size', '1 Kg').strip() or '1 Kg'
                    retail_price = float(row.get('retail_price', '0') or '0')
                    purchase_price = float(row.get('purchase_price', '0') or '0')
                    wholesale_price = float(row.get('wholesale_price', '0') or '0')
                    min_stock = int(row.get('min_stock_alert', '10') or '10')

                    # Resolve FKs by name
                    crop_type = None
                    if row.get('crop_type'):
                        crop_type, _ = CropType.objects.get_or_create(name=row['crop_type'].strip())

                    category = None
                    if row.get('category'):
                        category, _ = SeedCategory.objects.get_or_create(name=row['category'].strip())

                    brand = None
                    if row.get('brand'):
                        brand, _ = Brand.objects.get_or_create(name=row['brand'].strip())

                    seed, was_created = Seed.objects.get_or_create(
                        name=name,
                        variety=variety,
                        defaults={
                            'crop_type': crop_type,
                            'category': category,
                            'brand': brand,
                            'packing_size': packing_size,
                            'retail_price': retail_price,
                            'purchase_price': purchase_price,
                            'wholesale_price': wholesale_price,
                            'min_stock_alert': min_stock,
                        }
                    )
                    if was_created:
                        created += 1
                    else:
                        skipped += 1
                except Exception as e:
                    errors.append(f'Row {row_num}: {str(e)}')
                    skipped += 1

            msg = f'Upload complete: {created} seeds created, {skipped} skipped/duplicates.'
            if errors:
                msg += f' Errors: {" | ".join(errors[:5])}'
            messages.success(request, msg)
            log_activity(request.user, 'CREATE', 'Seeds', f'Bulk upload: {created} seeds imported', request)
        except Exception as e:
            messages.error(request, f'Error reading CSV: {str(e)}')

        return redirect('seeds:seed_list')


class SeedSampleCSVView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="seed_bulk_upload_sample.csv"'
        writer = csv.writer(response)
        writer.writerow(['name', 'variety', 'crop_type', 'category', 'brand', 'packing_size', 'retail_price', 'purchase_price', 'wholesale_price', 'min_stock_alert'])
        writer.writerow(['Hybrid Wheat', 'Pak-11', 'Wheat', 'Hybrid', 'National Seeds', '50 Kg Bag', '3500', '3000', '3200', '20'])
        writer.writerow(['Gold Corn', 'Super Gold', 'Maize/Corn', 'Open Pollinated', 'Monsanto', '10 Kg Bag', '1800', '1500', '1650', '10'])
        return response
