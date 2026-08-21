from django.urls import path
from . import views

app_name = 'voice'

urlpatterns = [
    path('process/', views.VoiceProcessView.as_view(), name='process'),
    path('approve/', views.VoiceApproveView.as_view(), name='approve'),
    path('cancel/', views.VoiceCancelView.as_view(), name='cancel'),
    path('select-choice/', views.VoiceSelectChoiceView.as_view(), name='select_choice'),
]
