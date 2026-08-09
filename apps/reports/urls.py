from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportsDashboardView.as_view(), name='reports_dashboard'),
    path('sales/', views.SalesReportView.as_view(), name='sales_report'),
    path('purchases/', views.PurchaseReportView.as_view(), name='purchase_report'),
    path('stock/', views.StockReportView.as_view(), name='stock_report'),
    path('customers/', views.CustomerReportView.as_view(), name='customer_report'),
    path('suppliers/', views.SupplierReportView.as_view(), name='supplier_report'),
    path('seeds/', views.SeedReportView.as_view(), name='seed_report'),
    path('low-stock/', views.LowStockReportView.as_view(), name='low_stock_report'),
    path('expired-stock/', views.ExpiredStockReportView.as_view(), name='expired_stock_report'),
]
