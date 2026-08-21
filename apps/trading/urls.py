from django.urls import path
from . import views

app_name = 'trading'

urlpatterns = [
    # Dashboard
    path('', views.TradingDashboardView.as_view(), name='dashboard'),

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
