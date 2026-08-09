from django import forms
from .models import SalesInvoice, Quotation

class SalesInvoiceForm(forms.ModelForm):
    class Meta:
        model = SalesInvoice
        fields = ('customer', 'sales_type', 'date', 'due_date', 'discount_amount', 'paid_amount', 'payment_method', 'reference_no', 'notes')
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select select2'}),
            'sales_type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference_no': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ('customer', 'date', 'valid_until', 'discount_amount', 'status', 'notes')
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select select2'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
