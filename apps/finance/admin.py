from django.contrib import admin
from .models import AccountCategory, ChartOfAccount, JournalVoucher, JournalItem

class JournalItemInline(admin.TabularInline):
    model = JournalItem
    extra = 2

@admin.register(AccountCategory)
class AccountCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(ChartOfAccount)
class ChartOfAccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('category', 'is_active')

@admin.register(JournalVoucher)
class JournalVoucherAdmin(admin.ModelAdmin):
    list_display = ('voucher_number', 'voucher_type', 'date', 'total_debit', 'total_credit', 'created_by')
    list_filter = ('voucher_type', 'date')
    search_fields = ('voucher_number', 'reference_no', 'description')
    inlines = [JournalItemInline]
