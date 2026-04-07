from django.contrib import admin
from django.urls import include, path

from core.views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('admin/', admin.site.urls),
    path('core/', include('core.urls')),
    path('teachers/', include('teachers.urls')),
    path('programs/', include('programs.urls')),
    path('competencies/', include('competencies.urls')),
    path('disciplines/', include('disciplines.urls')),
    path('assessment/', include('assessment.urls')),
    path('reports/', include('reports.urls')),
    path('export/', include('export.urls')),
]
