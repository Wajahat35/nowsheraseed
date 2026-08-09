from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.SalesListView.as_view(), name='sales_list'),
    path('add/', views.SalesCreateView.as_view(), name='sales_create'),
    path('<int:pk>/', views.SalesDetailView.as_view(), name='sales_detail'),
    path('<int:pk>/payment/', views.RecordPaymentView.as_view(), name='record_payment'),
    path('<int:pk>/print/', views.SalesPrintInvoiceView.as_view(), name='invoice_print'),
    path('<int:pk>/regenerate-qr/', views.RegenerateQRView.as_view(), name='regenerate_qr'),
    path('verify/<str:invoice_number>/', views.InvoiceQRVerifyView.as_view(), name='invoice_verify'),
    path('pos/', views.PosTerminalView.as_view(), name='pos_terminal'),
    path('quotations/', views.QuotationListView.as_view(), name='quotation_list'),
]
