from django.urls import path
from . import views

app_name = 'trading'

urlpatterns = [
    # Dashboard
    path('', views.TradingDashboardView.as_view(), name='dashboard'),

    # Seed Trading Sales Invoices
    path('sales/', views.TradingSalesListView.as_view(), name='sales_list'),
    path('sales/add/', views.TradingSalesCreateView.as_view(), name='sales_create'),
    path('sales/<int:pk>/', views.TradingSalesDetailView.as_view(), name='sales_detail'),
    path('sales/<int:pk>/edit/', views.TradingSalesUpdateView.as_view(), name='sales_edit'),
    path('sales/<int:pk>/delete/', views.TradingSalesDeleteView.as_view(), name='sales_delete'),

    # Seed Trading Purchase Invoices
    path('purchases/', views.TradingPurchaseListView.as_view(), name='purchase_list'),
    path('purchases/add/', views.TradingPurchaseCreateView.as_view(), name='purchase_create'),
    path('purchases/<int:pk>/', views.TradingPurchaseDetailView.as_view(), name='purchase_detail'),
    path('purchases/<int:pk>/edit/', views.TradingPurchaseUpdateView.as_view(), name='purchase_edit'),
    path('purchases/<int:pk>/delete/', views.TradingPurchaseDeleteView.as_view(), name='purchase_delete'),

    # Seed Trading Gate Passes
    path('gatepass/', views.TradingGatePassListView.as_view(), name='gatepass_list'),
    path('gatepass/add/', views.TradingGatePassCreateView.as_view(), name='gatepass_create'),
    path('gatepass/<int:pk>/', views.TradingGatePassDetailView.as_view(), name='gatepass_detail'),
    path('gatepass/<int:pk>/edit/', views.TradingGatePassUpdateView.as_view(), name='gatepass_edit'),
    path('gatepass/<int:pk>/delete/', views.TradingGatePassDeleteView.as_view(), name='gatepass_delete'),

    # Accounts
    path('accounts/', views.TradingAccountListView.as_view(), name='account_list'),
    path('accounts/add/', views.TradingAccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/', views.TradingAccountDetailView.as_view(), name='account_detail'),
    path('accounts/<int:pk>/edit/', views.TradingAccountUpdateView.as_view(), name='account_edit'),
    path('accounts/<int:pk>/delete/', views.TradingAccountDeleteView.as_view(), name='account_delete'),
    path('accounts/<int:pk>/toggle/', views.TradingAccountToggleView.as_view(), name='account_toggle'),

    # Deposits
    path('deposits/', views.DepositListView.as_view(), name='deposit_list'),
    path('deposits/add/', views.DepositCreateView.as_view(), name='deposit_create'),
    path('deposits/<int:pk>/edit/', views.DepositUpdateView.as_view(), name='deposit_edit'),
    path('deposits/<int:pk>/delete/', views.DepositDeleteView.as_view(), name='deposit_delete'),

    # Withdrawals
    path('withdrawals/', views.WithdrawalListView.as_view(), name='withdrawal_list'),
    path('withdrawals/add/', views.WithdrawalCreateView.as_view(), name='withdrawal_create'),
    path('withdrawals/<int:pk>/edit/', views.WithdrawalUpdateView.as_view(), name='withdrawal_edit'),
    path('withdrawals/<int:pk>/delete/', views.WithdrawalDeleteView.as_view(), name='withdrawal_delete'),

    # Trades
    path('trades/', views.TradeListView.as_view(), name='trade_list'),
    path('trades/add/', views.TradeCreateView.as_view(), name='trade_create'),
    path('trades/<int:pk>/', views.TradeDetailView.as_view(), name='trade_detail'),
    path('trades/<int:pk>/edit/', views.TradeUpdateView.as_view(), name='trade_edit'),
    path('trades/<int:pk>/delete/', views.TradeDeleteView.as_view(), name='trade_delete'),

    # Reports & Exports
    path('reports/', views.TradingReportsView.as_view(), name='reports'),
    path('export/csv/', views.ExportTradingCSVView.as_view(), name='export_csv'),
    path('export/excel/', views.ExportTradingExcelView.as_view(), name='export_excel'),
    path('export/pdf/', views.ExportTradingPDFView.as_view(), name='export_pdf'),
]
