from django.urls import path
from . import views

app_name = 'gatepass'

urlpatterns = [
    path('', views.GatePassListView.as_view(), name='gatepass_list'),
    path('add/', views.GatePassCreateView.as_view(), name='gatepass_create'),
    path('report/', views.GatePassReportView.as_view(), name='gatepass_report'),
    path('api/invoice-info/', views.InvoiceDetailsApiView.as_view(), name='invoice_api'),
    path('<int:pk>/', views.GatePassDetailView.as_view(), name='gatepass_detail'),
    path('<int:pk>/print/', views.GatePassPrintView.as_view(), name='gatepass_print'),
    path('<int:pk>/verify/', views.GatePassVerifyView.as_view(), name='gatepass_verify'),
    path('<int:pk>/inward-stock/', views.InwardStockActionView.as_view(), name='inward_stock'),
]
