from django import forms
from decimal import Decimal
from .models import WastageType, WastageInvoice, WastageRateHistory

class WastageTypeForm(forms.ModelForm):
    class Meta:
        model = WastageType
        fields = ('name', 'price_per_kg', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Broken Seed / Husk / Low-grade Screenings'}),
            'price_per_kg': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01', 'placeholder': 'e.g. 45.00'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Particle size, purity, feed grade...'}),
        }


class WastageRateUpdateForm(forms.Form):
    wastage_type_id = forms.IntegerField(widget=forms.HiddenInput())
    new_rate = forms.DecimalField(
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control font-monospace fs-5 fw-bold', 'step': '0.01', 'placeholder': 'New Price (PKR/KG)'})
    )
    reason = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Market price increase / bulk contract rate'})
    )


class WastageInvoiceForm(forms.ModelForm):
    class Meta:
        model = WastageInvoice
        fields = (
            'date', 'buyer_name', 'buyer_phone', 'buyer_address',
            'discount_amount', 'paid_amount', 'payment_method', 'reference_no', 'remarks'
        )
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'buyer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Haji Rafiq Feed Mills'}),
            'buyer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0300-1234567'}),
            'buyer_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mill / Warehouse Address, City'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01', 'value': '0.00'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01', 'value': '0.00'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Truck LES-5502 / Cash Slip'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dispatch notes, loading weight slip info...'}),
        }
