from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.CustomerListView.as_view(), name='customer_list'),
    path('add/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    path('<int:pk>/ledger/', views.CustomerLedgerView.as_view(), name='customer_ledger'),
    path('bulk-upload/', views.CustomerBulkUploadView.as_view(), name='bulk_upload'),
    path('sample-csv/', views.CustomerSampleCSVView.as_view(), name='sample_csv'),
]
