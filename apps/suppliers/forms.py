from django import forms
from .models import Supplier

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ('name', 'company_name', 'cnic', 'ntn', 'phone', 'whatsapp', 'email', 'address', 'city', 'opening_balance', 'bank_details', 'notes', 'is_active')
        labels = {
            'name': 'Grower Name *',
            'company_name': 'Farm / Organization Name',
            'cnic': 'CNIC (National Identity Card)',
            'ntn': 'NTN (Tax Number)',
            'phone': 'Contact Phone Number *',
            'whatsapp': 'WhatsApp Number',
            'email': 'Email Address',
            'address': 'Farm / Delivery Address',
            'city': 'City / Tehsil',
            'opening_balance': 'Opening Balance Payable (PKR)',
            'bank_details': 'Bank Account & Payment Details',
            'notes': 'Special Notes / Grower Agreement Terms',
            'is_active': 'Active Status',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Haji Muhammad Aslam', 'required': 'required'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Aslam Agri Farms'}),
            'cnic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '35202-XXXXXXX-X'}),
            'ntn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional NTN'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0300-XXXXXXX', 'required': 'required'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0300-XXXXXXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'grower@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Village, Tehsil, District'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bank_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Bank Name, Account Title, IBAN'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

GrowerForm = SupplierForm
