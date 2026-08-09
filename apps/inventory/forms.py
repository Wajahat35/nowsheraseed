from django import forms
from .models import StockAdjustment, Warehouse

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ('adjustment_type', 'seed', 'batch', 'quantity', 'reason')
        widgets = {
            'adjustment_type': forms.Select(attrs={'class': 'form-select'}),
            'seed': forms.Select(attrs={'class': 'form-select', 'id': 'id_seed'}),
            'batch': forms.Select(attrs={'class': 'form-select', 'id': 'id_batch'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for adjustment/damage write-off...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        adjustment_type = cleaned_data.get('adjustment_type')
        batch = cleaned_data.get('batch')
        quantity = cleaned_data.get('quantity')
        seed = cleaned_data.get('seed')

        # For deduction types, validate quantity does not exceed available stock
        if adjustment_type in ['DEDUCTION', 'DAMAGE', 'EXPIRED'] and quantity:
            if batch:
                available = batch.current_qty
            elif seed:
                from apps.seeds.models import SeedBatch
                batches = SeedBatch.objects.filter(seed=seed)
                available = sum(b.current_qty for b in batches)
            else:
                available = 0
            
            if quantity > available:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f'Cannot deduct {quantity} bags. Only {available} bags available in stock. Please check the quantity.'
                )
        return cleaned_data

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }
