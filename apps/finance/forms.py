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

from django.utils import timezone

class JournalVoucherForm(forms.ModelForm):
    class Meta:
        model = JournalVoucher
        fields = ('date', 'voucher_type', 'reference_no', 'description')
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'voucher_type': forms.HiddenInput(),
            'reference_no': forms.HiddenInput(),
            'description': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('date') and not (self.instance and self.instance.pk and self.instance.date):
            self.initial['date'] = timezone.now().date().strftime('%Y-%m-%d')
        if not self.initial.get('voucher_type'):
            self.initial['voucher_type'] = 'JV'
        self.fields['voucher_type'].required = False
        self.fields['reference_no'].required = False
        self.fields['description'].required = False
