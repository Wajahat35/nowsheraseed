from django import forms
from .models import TradingAccount, Deposit, Withdrawal, Trade

class TradingAccountForm(forms.ModelForm):
    class Meta:
        model = TradingAccount
        fields = (
            'name', 'broker_name', 'account_number', 'account_type',
            'platform', 'currency', 'initial_balance', 'opening_date',
            'is_active', 'notes'
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Personal Forex MT5'}),
            'broker_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Exness, IC Markets'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 50912839'}),
            'account_type': forms.Select(attrs={'class': 'form-select'}),
            'platform': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'USD'}),
            'initial_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '1000.00'}),
            'opening_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ('account', 'deposit_date', 'amount', 'currency', 'payment_method', 'transaction_id', 'notes')
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'deposit_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_method': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Bank Wire, USDT'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction Ref / Hash'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class WithdrawalForm(forms.ModelForm):
    class Meta:
        model = Withdrawal
        fields = ('account', 'withdrawal_date', 'amount', 'currency', 'payment_method', 'transaction_id', 'notes')
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'withdrawal_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_method': forms.TextInput(attrs={'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class TradeForm(forms.ModelForm):
    class Meta:
        model = Trade
        fields = (
            'account', 'trade_date', 'symbol', 'market_type', 'direction',
            'lot_size', 'entry_price', 'exit_price', 'stop_loss', 'take_profit',
            'commission', 'swap_fee', 'profit_loss', 'status', 'strategy', 'notes'
        )
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'trade_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'symbol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EURUSD, XAUUSD, BTCUSDT'}),
            'market_type': forms.Select(attrs={'class': 'form-select'}),
            'direction': forms.Select(attrs={'class': 'form-select'}),
            'lot_size': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': '0.10'}),
            'entry_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00001', 'placeholder': '1.08500'}),
            'exit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00001', 'placeholder': '1.09000'}),
            'stop_loss': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00001'}),
            'take_profit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00001'}),
            'commission': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'swap_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'profit_loss': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '150.00'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'strategy': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Trend Following, Scalping'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
