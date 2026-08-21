from django.contrib import admin
from .models import TradingAccount, Deposit, Withdrawal, Trade

@admin.register(TradingAccount)
class TradingAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'broker_name', 'account_number', 'platform', 'account_type', 'currency', 'current_balance', 'current_equity', 'is_active', 'opening_date')
    list_filter = ('platform', 'account_type', 'is_active', 'currency')
    search_fields = ('name', 'broker_name', 'account_number')

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('account', 'deposit_date', 'amount', 'currency', 'payment_method', 'transaction_id')
    list_filter = ('currency', 'payment_method', 'deposit_date')
    search_fields = ('account__name', 'transaction_id')

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('account', 'withdrawal_date', 'amount', 'currency', 'payment_method', 'transaction_id')
    list_filter = ('currency', 'payment_method', 'withdrawal_date')
    search_fields = ('account__name', 'transaction_id')

@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'account', 'market_type', 'direction', 'lot_size', 'entry_price', 'exit_price', 'profit_loss', 'status', 'trade_date')
    list_filter = ('market_type', 'direction', 'status', 'trade_date')
    search_fields = ('symbol', 'strategy', 'account__name')
