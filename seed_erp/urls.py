from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from apps.accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', account_views.UserLoginView.as_view(), name='login'),
    path('select-module/', account_views.SelectModuleView.as_view(), name='select_module'),
    path('', include('apps.dashboard.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('settings/', include('apps.settings_app.urls')),
    path('customers/', include('apps.customers.urls')),
    path('suppliers/', include('apps.suppliers.urls')),
    path('seeds/', include('apps.seeds.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('purchases/', include('apps.purchases.urls')),
    path('sales/', include('apps.sales.urls')),
    path('gatepass/', include('apps.gatepass.urls')),
    path('finance/', include('apps.finance.urls')),
    path('expenses/', include('apps.expenses.urls')),
    path('reports/', include('apps.reports.urls')),
    path('trading/', include('apps.trading.urls')),

    # Direct static & media serving for uploaded company logos, barcodes & QR codes
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
