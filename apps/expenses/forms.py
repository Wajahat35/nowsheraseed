from django import forms
from .models import Expense, ExpenseCategory

class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ('category', 'amount', 'payment_method', 'date', 'reference_no', 'description', 'receipt_attachment')
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),

            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference_no': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'receipt_attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
