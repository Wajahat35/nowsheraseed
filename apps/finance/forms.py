from django import forms
from .models import ChartOfAccount, JournalVoucher, AccountCategory

class ChartOfAccountForm(forms.ModelForm):
    class Meta:
        model = ChartOfAccount
        fields = ('code', 'name', 'category', 'description', 'is_active')
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1020'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class JournalVoucherForm(forms.ModelForm):
    class Meta:
        model = JournalVoucher
        fields = ('voucher_type', 'date', 'reference_no', 'description')
        widgets = {
            'voucher_type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference_no': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
