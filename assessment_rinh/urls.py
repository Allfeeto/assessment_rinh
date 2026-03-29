from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('core/', include('core.urls')),
    path('competencies/', include('competencies.urls')),
    path('disciplines/', include('disciplines.urls')),
    path('assessment/', include('assessment.urls')),
    path('reports/', include('reports.urls')),
    path('export/', include('export.urls')),
]