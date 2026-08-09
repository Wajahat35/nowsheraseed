from django.urls import path
from . import views

app_name = 'settings_app'

urlpatterns = [
    path('company/', views.CompanySettingsView.as_view(), name='company_settings'),
]
