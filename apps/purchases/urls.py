from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    path('', views.PurchaseListView.as_view(), name='purchase_list'),
    path('add/', views.PurchaseCreateView.as_view(), name='purchase_create'),
    path('<int:pk>/', views.PurchaseDetailView.as_view(), name='purchase_detail'),
    path('<int:pk>/payment/', views.RecordPurchasePaymentView.as_view(), name='record_payment'),
    path('<int:pk>/print/', views.PurchasePrintView.as_view(), name='purchase_print'),
]
