from django.contrib import admin
from .models import CropType, SeedCategory, Brand, Seed, SeedBatch

@admin.register(CropType)
class CropTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(SeedCategory)
class SeedCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_name')

@admin.register(Seed)
class SeedAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'variety', 'crop_type', 'category', 'brand', 'retail_price', 'status')
    search_fields = ('code', 'name', 'variety', 'barcode')
    list_filter = ('crop_type', 'category', 'brand', 'status')

@admin.register(SeedBatch)
class SeedBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_number', 'lot_number', 'seed', 'manufacturing_date', 'expiry_date', 'current_qty', 'sale_price')
    search_fields = ('batch_number', 'lot_number', 'seed__name')
    list_filter = ('expiry_date',)
