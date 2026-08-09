from django import forms
from .models import Customer

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ('name', 'father_name', 'company_name', 'cnic', 'ntn', 'phone', 'whatsapp', 'email', 'address', 'city', 'opening_balance', 'debit_limit', 'credit_days', 'notes', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'cnic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '35202-XXXXXXX-X'}),
            'ntn': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'debit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'credit_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
