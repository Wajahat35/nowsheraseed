from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Role

class CustomUserCreationForm(UserCreationForm):
    role = forms.ModelChoiceField(queryset=Role.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'cnic', 'designation', 'role', 'avatar')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'cnic': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'role':
                self.fields[field].widget.attrs.update({'class': 'form-control'})

class CustomUserChangeForm(UserChangeForm):
    password = None  # Exclude password field in edit form
    role = forms.ModelChoiceField(queryset=Role.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'cnic', 'designation', 'role', 'is_active', 'avatar')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'cnic': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }
