from django.urls import path

from .views import ProgramDisciplineListView

urlpatterns = [
    path('list/', ProgramDisciplineListView.as_view(), name='program_discipline_list'),
]