from django import forms
from .models import PurchaseInvoice, PurchaseItem

class PurchaseInvoiceForm(forms.ModelForm):
    class Meta:
        model = PurchaseInvoice
        fields = ('supplier', 'supplier_bill_no', 'date', 'due_date', 'discount_amount', 'paid_amount', 'payment_method', 'reference_no', 'notes')
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select select2'}),
            'supplier_bill_no': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference_no': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
