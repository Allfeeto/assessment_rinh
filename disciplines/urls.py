from django.urls import path

from .views import DisciplinePageDetailView, DisciplinePageListView, ProgramDisciplineListView

urlpatterns = [
    path('', DisciplinePageListView.as_view(), name='discipline_page_list'),
    path('<int:pk>/', DisciplinePageDetailView.as_view(), name='discipline_page_detail'),
    path('list/', ProgramDisciplineListView.as_view(), name='program_discipline_list'),
]
