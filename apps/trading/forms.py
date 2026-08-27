from django import forms
from .models import TradingAccount, Deposit, Withdrawal, Trade, TradingSalesInvoice, TradingPurchaseInvoice, TradingGatePass

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


# ---------------------------------------------------------------------------
# SEEDS TRADING OPERATIONAL FORMS (MIAN TRADERS)
# ---------------------------------------------------------------------------
class TradingSalesInvoiceForm(forms.ModelForm):
    class Meta:
        model = TradingSalesInvoice
        fields = ('date', 'customer_name', 'phone', 'crop_name', 'crop_weight', 'rate_per_40kg', 'total_amount', 'paid_amount', 'remarks')
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Tariq Seed Traders'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0300-1234567'}),
            'crop_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wheat / Paddy Rice / Maize'}),
            'crop_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g. 2000.00 (Kg)', 'id': 'id_crop_weight'}),
            'rate_per_40kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g. 4800.00 (per 40kg)', 'id': 'id_rate_per_40kg'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Auto Calculated', 'id': 'id_total_amount'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class TradingPurchaseInvoiceForm(forms.ModelForm):
    class Meta:
        model = TradingPurchaseInvoice
        fields = ('date', 'supplier_name', 'phone', 'crop_name', 'crop_weight', 'rate_per_40kg', 'total_amount', 'paid_amount', 'remarks')
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'supplier_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Punjab Seed Growers'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0300-9876543'}),
            'crop_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wheat / Paddy Rice / Maize'}),
            'crop_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g. 2000.00 (Kg)', 'id': 'id_crop_weight'}),
            'rate_per_40kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g. 4800.00 (per 40kg)', 'id': 'id_rate_per_40kg'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Auto Calculated', 'id': 'id_total_amount'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class TradingGatePassForm(forms.ModelForm):
    class Meta:
        model = TradingGatePass
        fields = (
            'pass_type', 'date', 'vehicle_no', 'driver_name', 'party_name',
            'seed_item', 'bags_qty', 'gross_weight', 'tare_weight', 'net_weight',
            'status', 'remarks'
        )
        widgets = {
            'pass_type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'vehicle_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. LES-4890'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Driver Name'}),
            'party_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer / Supplier Name'}),
            'seed_item': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wheat Seed Faisalabad 2008'}),
            'bags_qty': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}),
            'gross_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '5000.00'}),
            'tare_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '1500.00'}),
            'net_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '3500.00'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
