from django.contrib import admin
from .models import Supplier

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'company_name', 'phone', 'city', 'opening_balance', 'is_active')
    search_fields = ('code', 'name', 'phone', 'company_name', 'cnic')
    list_filter = ('city', 'is_active')
