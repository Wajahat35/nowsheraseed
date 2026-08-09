from django.contrib import admin
from .models import StockMovement, StockAdjustment, Warehouse

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'location')

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'movement_type', 'seed', 'batch', 'quantity', 'reference_no', 'user')
    list_filter = ('movement_type', 'created_at')

@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'adjustment_type', 'seed', 'batch', 'quantity', 'adjusted_by')
    list_filter = ('adjustment_type', 'date')
