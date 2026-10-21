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


class SeedProcessingForm(forms.ModelForm):
    class Meta:
        from .models import SeedProcessing
        model = SeedProcessing
        fields = (
            'date', 'grower', 'seed', 'raw_input_kg',
            'clean_seed_kg', 'wastage_kg', 'wastage_type',
            'moisture_dust_loss_kg', 'notes'
        )
        labels = {
            'date': 'Processing Date *',
            'grower': 'Grower (Source Intake) *',
            'seed': 'Seed Variety / Crop *',
            'raw_input_kg': 'Total Raw Seed Input (KG) *',
            'clean_seed_kg': 'Clean / Usable Seed Output (KG) *',
            'wastage_kg': 'Wastage / By-Product Output (KG)',
            'wastage_type': 'Wastage Grade / Type',
            'moisture_dust_loss_kg': 'Moisture & Dust Loss (KG)',
            'notes': 'Inspection & Quality Notes',
        }
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'grower': forms.Select(attrs={'class': 'form-select select2-enable', 'id': 'id_grower'}),
            'seed': forms.Select(attrs={'class': 'form-select select2-enable', 'id': 'id_seed_select'}),
            'raw_input_kg': forms.NumberInput(attrs={'class': 'form-control font-monospace fs-5 fw-bold', 'step': '0.01', 'id': 'id_raw_input_kg', 'placeholder': 'e.g. 5000.00'}),
            'clean_seed_kg': forms.NumberInput(attrs={'class': 'form-control font-monospace fs-5 fw-bold text-success', 'step': '0.01', 'id': 'id_clean_seed_kg', 'placeholder': 'e.g. 4600.00'}),
            'wastage_kg': forms.NumberInput(attrs={'class': 'form-control font-monospace fs-5 fw-bold text-danger', 'step': '0.01', 'id': 'id_wastage_kg', 'placeholder': 'e.g. 350.00'}),
            'wastage_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_wastage_type'}),
            'moisture_dust_loss_kg': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01', 'id': 'id_moisture_dust_loss_kg', 'placeholder': '0.00'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Moisture % test results, screening screen mesh, etc.'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        from decimal import Decimal
        raw = Decimal(str(cleaned_data.get('raw_input_kg') or 0))
        clean = Decimal(str(cleaned_data.get('clean_seed_kg') or 0))
        wst = Decimal(str(cleaned_data.get('wastage_kg') or 0))
        loss = Decimal(str(cleaned_data.get('moisture_dust_loss_kg') or 0))

        if raw <= Decimal('0'):
            self.add_error('raw_input_kg', 'Raw input weight must be greater than 0 KG.')

        if clean < Decimal('0'):
            self.add_error('clean_seed_kg', 'Clean seed weight cannot be negative.')

        if wst < Decimal('0'):
            self.add_error('wastage_kg', 'Wastage weight cannot be negative.')

        if (clean + wst) > raw:
            self.add_error('clean_seed_kg', f"Clean Seed ({clean} KG) + Wastage ({wst} KG) cannot exceed Raw Input ({raw} KG).")

        # Equation validation
        computed = clean + wst + loss
        if abs(raw - computed) > Decimal('0.05'):
            # Auto-balance into loss if loss was 0
            if loss == Decimal('0') and raw >= (clean + wst):
                cleaned_data['moisture_dust_loss_kg'] = raw - (clean + wst)
            else:
                raise forms.ValidationError(
                    f"Equation mismatch: Total Raw Input ({raw:,.2f} KG) must equal Clean Seed ({clean:,.2f} KG) + Wastage ({wst:,.2f} KG) + Loss ({loss:,.2f} KG). Current total: {computed:,.2f} KG."
                )

        if wst > Decimal('0') and not cleaned_data.get('wastage_type'):
            self.add_error('wastage_type', 'Please select a Wastage Grade/Type since wastage quantity is recorded.')

        return cleaned_data
