from django.urls import path

from .views import ReportsDashboardView

urlpatterns = [
    path('', ReportsDashboardView.as_view(), name='reports_dashboard'),
]