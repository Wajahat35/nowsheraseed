from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    path('', views.SupplierListView.as_view(), name='supplier_list'),
    path('add/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_update'),
    path('<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),
    path('<int:pk>/ledger/', views.SupplierLedgerView.as_view(), name='supplier_ledger'),
    path('bulk-upload/', views.SupplierBulkUploadView.as_view(), name='bulk_upload'),
    path('sample-csv/', views.SupplierSampleCSVView.as_view(), name='sample_csv'),
]
