from django.contrib import admin
from .models import GatePass

@admin.register(GatePass)
class GatePassAdmin(admin.ModelAdmin):
    list_display = ('pass_number', 'pass_type', 'vehicle_number', 'driver_name', 'total_bags', 'total_weight_kg', 'status', 'date_time')
    list_filter = ('pass_type', 'status', 'date_time')
    search_fields = ('pass_number', 'vehicle_number', 'driver_name', 'driver_cnic', 'invoice_reference')
