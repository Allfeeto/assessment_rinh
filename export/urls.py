from django.urls import path
from django.views.generic import RedirectView

from .views import WordExportView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='export_word', permanent=False), name='export_root'),
    path('word/', WordExportView.as_view(), name='export_word'),
]