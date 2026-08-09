from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from .models import CompanyProfile
from .forms import CompanyProfileForm
from apps.accounts.views import AdminRequiredMixin, log_activity

class CompanySettingsView(LoginRequiredMixin, AdminRequiredMixin, View):
    template_name = 'settings_app/company_profile.html'

    def get(self, request):
        company = CompanyProfile.get_instance()
        form = CompanyProfileForm(instance=company)
        return render(request, self.template_name, {'form': form, 'company': company})

    def post(self, request):
        company = CompanyProfile.get_instance()
        form = CompanyProfileForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            log_activity(request.user, 'UPDATE', 'Settings', "Updated Company Profile Settings", request)
            messages.success(request, "Company Profile updated successfully!")
            return redirect('settings_app:company_settings')
        return render(request, self.template_name, {'form': form, 'company': company})
