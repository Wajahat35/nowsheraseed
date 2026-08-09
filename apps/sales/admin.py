from django.contrib import admin
from .models import SalesInvoice, SalesItem, Quotation, QuotationItem

class SalesItemInline(admin.TabularInline):
    model = SalesItem
    extra = 1

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'sales_type', 'date', 'grand_total', 'paid_amount', 'payment_status')
    list_filter = ('sales_type', 'payment_status', 'date')
    search_fields = ('invoice_number', 'customer__name')
    inlines = [SalesItemInline]

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('quotation_number', 'customer', 'date', 'valid_until', 'grand_total', 'status')
    list_filter = ('status', 'date')
