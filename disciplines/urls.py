from django.urls import path

from .views import (
    DisciplinesDashboardView,
    DisciplineCreateView,
    DisciplineDeleteView,
    DisciplineDetailView,
    DisciplineListView,
    DisciplineUpdateView,
    ProgramDisciplineCreateView,
    ProgramDisciplineDeleteView,
    ProgramDisciplineDetailView,
    ProgramDisciplineListView,
    ProgramDisciplineUpdateView,
    program_discipline_by_program,
)

urlpatterns = [
    path('', DisciplinesDashboardView.as_view(), name='disciplines_root'),

    path('list/', DisciplineListView.as_view(), name='disciplines_discipline_list'),
    path('list/create/', DisciplineCreateView.as_view(), name='disciplines_discipline_create'),
    path('list/<int:pk>/', DisciplineDetailView.as_view(), name='disciplines_discipline_detail'),
    path('list/<int:pk>/edit/', DisciplineUpdateView.as_view(), name='disciplines_discipline_update'),
    path('list/<int:pk>/delete/', DisciplineDeleteView.as_view(), name='disciplines_discipline_delete'),

    path('program-disciplines/', ProgramDisciplineListView.as_view(), name='disciplines_program_discipline_list'),
    path('program-disciplines/create/', ProgramDisciplineCreateView.as_view(), name='disciplines_program_discipline_create'),
    path('program-disciplines/<int:pk>/', ProgramDisciplineDetailView.as_view(), name='disciplines_program_discipline_detail'),
    path('program-disciplines/<int:pk>/edit/', ProgramDisciplineUpdateView.as_view(), name='disciplines_program_discipline_update'),
    path('program-disciplines/<int:pk>/delete/', ProgramDisciplineDeleteView.as_view(), name='disciplines_program_discipline_delete'),

    path('by-program/', program_discipline_by_program, name='disciplines_program_discipline_by_program'),
]
