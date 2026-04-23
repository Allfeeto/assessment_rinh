from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
    ),
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view()),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
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
