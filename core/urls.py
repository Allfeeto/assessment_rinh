from django.urls import path

from .views import EducationalProgramListView

urlpatterns = [
    path('programs/', EducationalProgramListView.as_view(), name='educational_program_list'),
]