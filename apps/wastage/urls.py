from django.urls import path
from . import views

app_name = 'wastage'

urlpatterns = [
    path('', views.WastageInventoryView.as_view(), name='wastage_inventory'),
    path('rate/update/', views.WastageRateUpdateView.as_view(), name='rate_update'),
    path('type/add/', views.WastageTypeCreateView.as_view(), name='type_create'),
    path('invoices/', views.WastageInvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', views.WastageInvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<int:pk>/', views.WastageInvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/delete/', views.WastageInvoiceDeleteView.as_view(), name='invoice_delete'),
]
