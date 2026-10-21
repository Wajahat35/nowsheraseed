from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.StockListView.as_view(), name='stock_list'),
    path('processing/', views.SeedProcessingListView.as_view(), name='processing_list'),
    path('processing/create/', views.SeedProcessingCreateView.as_view(), name='processing_create'),
    path('processing/<int:pk>/', views.SeedProcessingDetailView.as_view(), name='processing_detail'),
    path('movements/', views.StockMovementListView.as_view(), name='movement_list'),
    path('adjustments/add/', views.StockAdjustmentCreateView.as_view(), name='adjustment_create'),
    path('valuation/', views.InventoryValuationView.as_view(), name='valuation'),
    path('api/batches-by-seed/', views.BatchesBySeedApiView.as_view(), name='batches_by_seed'),
]
