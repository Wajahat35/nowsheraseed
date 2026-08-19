from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('coa/', views.COAListView.as_view(), name='coa_list'),
    path('coa/add/', views.COACreateView.as_view(), name='coa_create'),
    path('vouchers/', views.VoucherListView.as_view(), name='voucher_list'),
    path('vouchers/add/', views.VoucherCreateView.as_view(), name='voucher_create'),
    path('vouchers/export/excel/', views.ExportVoucherListExcelView.as_view(), name='voucher_list_excel'),
    path('vouchers/export/pdf/', views.ExportVoucherListPDFView.as_view(), name='voucher_list_pdf'),
    path('vouchers/<int:pk>/', views.VoucherDetailView.as_view(), name='voucher_detail'),
    path('vouchers/<int:pk>/edit/', views.VoucherUpdateView.as_view(), name='voucher_edit'),
    path('vouchers/<int:pk>/delete/', views.VoucherDeleteView.as_view(), name='voucher_delete'),
    path('vouchers/<int:pk>/export/excel/', views.ExportVoucherDetailExcelView.as_view(), name='voucher_detail_excel'),
    path('vouchers/<int:pk>/export/pdf/', views.ExportVoucherDetailPDFView.as_view(), name='voucher_detail_pdf'),
    path('ledger/', views.GeneralLedgerView.as_view(), name='general_ledger'),
    path('trial-balance/', views.TrialBalanceView.as_view(), name='trial_balance'),
    path('profit-loss/', views.ProfitLossView.as_view(), name='profit_loss'),
    path('balance-sheet/', views.BalanceSheetView.as_view(), name='balance_sheet'),
    path('cash-book/', views.CashBookView.as_view(), name='cash_book'),
    path('bank-book/', views.BankBookView.as_view(), name='bank_book'),
]
