from django.contrib import admin
from .models import WastageType, WastageRateHistory, WastageStock, WastageMovement, WastageInvoice, WastageInvoiceItem

@admin.register(WastageType)
class WastageTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_per_kg', 'updated_at')
    search_fields = ('name',)

@admin.register(WastageRateHistory)
class WastageRateHistoryAdmin(admin.ModelAdmin):
    list_display = ('wastage_type', 'old_rate', 'new_rate', 'changed_by', 'created_at')
    list_filter = ('wastage_type',)

@admin.register(WastageStock)
class WastageStockAdmin(admin.ModelAdmin):
    list_display = ('wastage_type', 'current_stock_kg', 'updated_at')

@admin.register(WastageMovement)
class WastageMovementAdmin(admin.ModelAdmin):
    list_display = ('movement_type', 'wastage_type', 'quantity_kg', 'reference_no', 'created_at')
    list_filter = ('movement_type', 'wastage_type')

class WastageInvoiceItemInline(admin.TabularInline):
    model = WastageInvoiceItem
    extra = 1

@admin.register(WastageInvoice)
class WastageInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'date', 'buyer_name', 'grand_total', 'paid_amount', 'payment_status')
    list_filter = ('payment_status', 'payment_method')
    search_fields = ('invoice_number', 'buyer_name', 'buyer_phone')
    inlines = [WastageInvoiceItemInline]
