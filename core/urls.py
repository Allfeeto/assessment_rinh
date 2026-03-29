from django.urls import path

from .views import EducationalProgramListView, HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('programs/', EducationalProgramListView.as_view(), name='educational_program_list'),
]
