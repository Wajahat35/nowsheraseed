import re
from django import forms
from django.core.exceptions import ValidationError
from .models import GatePass
from apps.sales.models import SalesInvoice
from apps.purchases.models import PurchaseInvoice

class GatePassForm(forms.ModelForm):
    invoice_reference = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2-enable', 'id': 'id_invoice_reference'}),
        help_text="Select Sales Invoice (INV-XXXX) or Purchase Bill (PUR-XXXX)"
    )

    class Meta:
        model = GatePass
        fields = ('pass_type', 'vehicle_number', 'driver_name', 'driver_cnic', 'driver_mobile', 'transport_company', 'invoice_reference', 'seed', 'batch', 'total_bags', 'total_weight_kg', 'remarks', 'status')
        widgets = {
            'pass_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_pass_type'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. LES-1234'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'driver_cnic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '42000-0000000-0'}),
            'driver_mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '03000000000'}),
            'transport_company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Faisal Movers / Self'}),
            'seed': forms.Select(attrs={'class': 'form-select select2-enable', 'id': 'id_seed'}),
            'batch': forms.Select(attrs={'class': 'form-select select2-enable', 'id': 'id_batch'}),
            'total_bags': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_total_bags'}),
            'total_weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_total_weight_kg'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].required = False
        self.fields['status'].initial = 'Issued'

        choices = [('', '-- Select Invoice / Bill Reference (Optional) --')]

        # Collect existing gate pass invoice references to prevent duplicate gate pass issuance
        existing_refs = set(
            GatePass.objects.exclude(invoice_reference__isnull=True)
                            .exclude(invoice_reference='')
                            .values_list('invoice_reference', flat=True)
        )
        current_ref = self.instance.invoice_reference if self.instance and self.instance.pk else None

        # Add Sales Invoices (exclude invoices with existing gate passes)
        try:
            sales_invoices = SalesInvoice.objects.order_by('-id')
            for inv in sales_invoices:
                if inv.invoice_number in existing_refs and inv.invoice_number != current_ref:
                    continue
                cust_name = inv.customer.name if inv.customer else "Walk-in Customer"
                total_qty = sum(item.quantity for item in inv.items.all())
                total_wgt = sum(item.quantity * item.seed.weight_kg for item in inv.items.all())
                choices.append((inv.invoice_number, f"Sales Invoice: {inv.invoice_number} ({cust_name} - {total_qty} Bags / {total_wgt} Kg)"))
        except Exception:
            pass

        # Add Purchase Bills (exclude purchase bills with existing gate passes)
        try:
            purchase_invoices = PurchaseInvoice.objects.order_by('-id')
            for pur in purchase_invoices:
                if pur.invoice_number in existing_refs and pur.invoice_number != current_ref:
                    continue
                supp_name = pur.supplier.name if pur.supplier else "Supplier"
                total_qty = sum(item.quantity for item in pur.items.all())
                total_wgt = sum(item.quantity * item.seed.weight_kg for item in pur.items.all())
                choices.append((pur.invoice_number, f"Purchase Bill: {pur.invoice_number} ({supp_name} - {total_qty} Bags / {total_wgt} Kg)"))
        except Exception:
            pass

        self.fields['invoice_reference'].choices = choices

    def clean_invoice_reference(self):
        ref = self.cleaned_data.get('invoice_reference')
        if ref:
            qs = GatePass.objects.filter(invoice_reference=ref)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                existing_gp = qs.first()
                raise ValidationError(f"A Gate Pass ({existing_gp.pass_number}) has already been issued for reference {ref}.")
        return ref

    def clean_driver_cnic(self):
        cnic = self.cleaned_data.get('driver_cnic')
        if not cnic:
            raise ValidationError("Driver CNIC is required.")
        cleaned = cnic.strip().replace(' ', '')
        # Check XXXXX-XXXXXXX-X format or 13 plain digits
        if re.match(r'^\d{5}-\d{7}-\d{1}$', cleaned):
            return cleaned
        raw_digits = cleaned.replace('-', '')
        if len(raw_digits) == 13 and raw_digits.isdigit():
            return f"{raw_digits[:5]}-{raw_digits[5:12]}-{raw_digits[12]}"
        raise ValidationError("CNIC must be a valid 13-digit Pakistani CNIC (e.g. 42000-0000000-0).")

    def clean_driver_mobile(self):
        mobile = self.cleaned_data.get('driver_mobile')
        if not mobile:
            raise ValidationError("Driver Mobile number is required.")
        cleaned = mobile.strip().replace('-', '').replace(' ', '')
        if not re.match(r'^03\d{9}$', cleaned):
            raise ValidationError("Mobile number must be an 11-digit number starting with 03 (e.g. 03000000000).")
        return cleaned

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('status'):
            cleaned_data['status'] = 'Issued'
        return cleaned_data
