from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('', views.ExpenseListView.as_view(), name='expense_list'),
    path('add/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense_edit'),
    path('<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense_delete'),
    path('categories/', views.ExpenseCategoryListView.as_view(), name='category_list'),
    path('quick-add-category/', views.QuickAddCategoryView.as_view(), name='quick_add_category'),
]
