from django.urls import path

from .views import (
    AcademicDegreeCreateView,
    AcademicDegreeDeleteView,
    AcademicDegreeDetailView,
    AcademicDegreeListView,
    AcademicDegreeUpdateView,
    AcademicTitleCreateView,
    AcademicTitleDeleteView,
    AcademicTitleDetailView,
    AcademicTitleListView,
    AcademicTitleUpdateView,
    AssessmentItemTypeCreateView,
    AssessmentItemTypeDeleteView,
    AssessmentItemTypeDetailView,
    AssessmentItemTypeListView,
    AssessmentItemTypeUpdateView,
    CompetenceTypeCreateView,
    CompetenceTypeDeleteView,
    CompetenceTypeDetailView,
    CompetenceTypeListView,
    CompetenceTypeUpdateView,
    EducationLevelCreateView,
    EducationLevelDeleteView,
    EducationLevelDetailView,
    EducationLevelListView,
    EducationLevelUpdateView,
    HomeView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='core_home'),

    path('education-levels/', EducationLevelListView.as_view(), name='core_education_level_list'),
    path('education-levels/create/', EducationLevelCreateView.as_view(), name='core_education_level_create'),
    path('education-levels/<int:pk>/', EducationLevelDetailView.as_view(), name='core_education_level_detail'),
    path('education-levels/<int:pk>/edit/', EducationLevelUpdateView.as_view(), name='core_education_level_update'),
    path('education-levels/<int:pk>/delete/', EducationLevelDeleteView.as_view(), name='core_education_level_delete'),

    path('competence-types/', CompetenceTypeListView.as_view(), name='core_competence_type_list'),
    path('competence-types/create/', CompetenceTypeCreateView.as_view(), name='core_competence_type_create'),
    path('competence-types/<int:pk>/', CompetenceTypeDetailView.as_view(), name='core_competence_type_detail'),
    path('competence-types/<int:pk>/edit/', CompetenceTypeUpdateView.as_view(), name='core_competence_type_update'),
    path('competence-types/<int:pk>/delete/', CompetenceTypeDeleteView.as_view(), name='core_competence_type_delete'),

    path('assessment-item-types/', AssessmentItemTypeListView.as_view(), name='core_assessment_item_type_list'),
    path('assessment-item-types/create/', AssessmentItemTypeCreateView.as_view(), name='core_assessment_item_type_create'),
    path('assessment-item-types/<int:pk>/', AssessmentItemTypeDetailView.as_view(), name='core_assessment_item_type_detail'),
    path('assessment-item-types/<int:pk>/edit/', AssessmentItemTypeUpdateView.as_view(), name='core_assessment_item_type_update'),
    path('assessment-item-types/<int:pk>/delete/', AssessmentItemTypeDeleteView.as_view(), name='core_assessment_item_type_delete'),

    path('academic-degrees/', AcademicDegreeListView.as_view(), name='core_academic_degree_list'),
    path('academic-degrees/create/', AcademicDegreeCreateView.as_view(), name='core_academic_degree_create'),
    path('academic-degrees/<int:pk>/', AcademicDegreeDetailView.as_view(), name='core_academic_degree_detail'),
    path('academic-degrees/<int:pk>/edit/', AcademicDegreeUpdateView.as_view(), name='core_academic_degree_update'),
    path('academic-degrees/<int:pk>/delete/', AcademicDegreeDeleteView.as_view(), name='core_academic_degree_delete'),

    path('academic-titles/', AcademicTitleListView.as_view(), name='core_academic_title_list'),
    path('academic-titles/create/', AcademicTitleCreateView.as_view(), name='core_academic_title_create'),
    path('academic-titles/<int:pk>/', AcademicTitleDetailView.as_view(), name='core_academic_title_detail'),
    path('academic-titles/<int:pk>/edit/', AcademicTitleUpdateView.as_view(), name='core_academic_title_update'),
    path('academic-titles/<int:pk>/delete/', AcademicTitleDeleteView.as_view(), name='core_academic_title_delete'),
]
