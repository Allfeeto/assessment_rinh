from django.urls import path

from .views import (
    CompetenceCreateView,
    CompetenceDeleteView,
    CompetenceDetailView,
    CompetenceListView,
    CompetenceUpdateView,
    DisciplineCompetenceCreateView,
    DisciplineCompetenceDeleteView,
    DisciplineCompetenceDetailView,
    DisciplineCompetenceListView,
    DisciplineCompetenceUpdateView,
    competences_by_program_discipline,
)

urlpatterns = [
    path('', CompetenceListView.as_view(), name='competencies_root'),

    path('list/', CompetenceListView.as_view(), name='competencies_competence_list'),
    path('list/create/', CompetenceCreateView.as_view(), name='competencies_competence_create'),
    path('list/<int:pk>/', CompetenceDetailView.as_view(), name='competencies_competence_detail'),
    path('list/<int:pk>/edit/', CompetenceUpdateView.as_view(), name='competencies_competence_update'),
    path('list/<int:pk>/delete/', CompetenceDeleteView.as_view(), name='competencies_competence_delete'),

    path('discipline-competence/', DisciplineCompetenceListView.as_view(), name='competencies_discipline_competence_list'),
    path('discipline-competence/create/', DisciplineCompetenceCreateView.as_view(), name='competencies_discipline_competence_create'),
    path('discipline-competence/<int:pk>/', DisciplineCompetenceDetailView.as_view(), name='competencies_discipline_competence_detail'),
    path('discipline-competence/<int:pk>/edit/', DisciplineCompetenceUpdateView.as_view(), name='competencies_discipline_competence_update'),
    path('discipline-competence/<int:pk>/delete/', DisciplineCompetenceDeleteView.as_view(), name='competencies_discipline_competence_delete'),

    path('by-program-discipline/', competences_by_program_discipline, name='competencies_by_program_discipline'),
]