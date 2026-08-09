from django.contrib import admin
from .models import CompanyProfile

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'city', 'currency_symbol', 'gst_rate')
