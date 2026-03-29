from django.urls import path

from .views import (
    AssessmentByTypeReportView,
    DisciplineCompetenceCountReportView,
    ProgramCompetenceCoverageReportView,
    ReportsPageView,
)

urlpatterns = [
    path('', ReportsPageView.as_view(), name='reports_page'),
    path('discipline-competence/', DisciplineCompetenceCountReportView.as_view(), name='report_discipline_competence'),
    path('program-competence-coverage/', ProgramCompetenceCoverageReportView.as_view(), name='report_program_competence_coverage'),
    path('assessment-by-type/', AssessmentByTypeReportView.as_view(), name='report_assessment_by_type'),
]
