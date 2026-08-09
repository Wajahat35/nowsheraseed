from django import forms
from .models import CropType, SeedCategory, Brand, Seed, SeedBatch

class CropTypeForm(forms.ModelForm):
    class Meta:
        model = CropType
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class SeedCategoryForm(forms.ModelForm):
    class Meta:
        model = SeedCategory
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }

class SeedForm(forms.ModelForm):
    class Meta:
        model = Seed
        fields = ('name', 'variety', 'crop_type', 'category', 'brand', 'packing_size', 'weight_kg', 'purchase_price', 'retail_price', 'wholesale_price', 'gst_rate', 'min_stock_alert', 'barcode', 'image', 'status')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'variety': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'crop_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'packing_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 20 Kg Bag'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'retail_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'wholesale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'gst_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_stock_alert': forms.NumberInput(attrs={'class': 'form-control'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class SeedBatchForm(forms.ModelForm):
    class Meta:
        model = SeedBatch
        fields = '__all__'
        widgets = {
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'lot_number': forms.TextInput(attrs={'class': 'form-control'}),
            'seed': forms.Select(attrs={'class': 'form-select'}),
            'manufacturing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'initial_qty': forms.NumberInput(attrs={'class': 'form-control'}),
            'current_qty': forms.NumberInput(attrs={'class': 'form-control'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
