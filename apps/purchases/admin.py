from django.contrib import admin
from .models import PurchaseInvoice, PurchaseItem

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'supplier', 'date', 'grand_total', 'paid_amount', 'payment_status')
    list_filter = ('payment_status', 'date')
    search_fields = ('invoice_number', 'supplier__name', 'supplier_bill_no')
    inlines = [PurchaseItemInline]
