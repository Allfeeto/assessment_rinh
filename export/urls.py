from django.urls import path

from .views import WordExportView

urlpatterns = [
    path('word/', WordExportView.as_view(), name='export_word'),
]