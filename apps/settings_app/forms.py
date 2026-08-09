from django import forms
from .models import CompanyProfile

class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control'}),
            'ntn': forms.TextInput(attrs={'class': 'form-control'}),
            'strn': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'erp_base_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. http://192.168.1.100:8000'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'invoice_prefix': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_prefix': forms.TextInput(attrs={'class': 'form-control'}),
            'gatepass_prefix': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_footer': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'invoice_logo': forms.FileInput(attrs={'class': 'form-control'}),
        }
