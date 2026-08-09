from django.urls import path
from . import views

app_name = 'seeds'

urlpatterns = [
    path('', views.SeedListView.as_view(), name='seed_list'),
    path('add/', views.SeedCreateView.as_view(), name='seed_create'),
    path('<int:pk>/edit/', views.SeedUpdateView.as_view(), name='seed_update'),
    path('<int:pk>/delete/', views.SeedDeleteView.as_view(), name='seed_delete'),
    path('<int:pk>/barcode/', views.BarcodePrintView.as_view(), name='barcode_print'),
    
    path('crops/', views.CropTypeListView.as_view(), name='crop_list'),
    path('categories/', views.SeedCategoryListView.as_view(), name='category_list'),
    path('brands/', views.BrandListView.as_view(), name='brand_list'),
    
    path('batches/', views.SeedBatchListView.as_view(), name='batch_list'),
    path('batches/add/', views.SeedBatchCreateView.as_view(), name='batch_create'),
    path('bulk-upload/', views.SeedBulkUploadView.as_view(), name='bulk_upload'),
    path('sample-csv/', views.SeedSampleCSVView.as_view(), name='sample_csv'),
]
