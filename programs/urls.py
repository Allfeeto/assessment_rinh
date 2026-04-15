from django.urls import path

from .views import (
    EducationalProgramCreateView,
    EducationalProgramDeleteView,
    EducationalProgramDetailView,
    EducationalProgramListView,
    EducationalProgramUpdateView,
    ProgramProfileCreateView,
    ProgramProfileDeleteView,
    ProgramProfileDetailView,
    ProgramProfileListView,
    ProgramProfileUpdateView,
    ProgramsDashboardView,
    TrainingDirectionCreateView,
    TrainingDirectionDeleteView,
    TrainingDirectionDetailView,
    TrainingDirectionListView,
    TrainingDirectionUpdateView,
    profiles_by_direction,
)

urlpatterns = [
    path('', ProgramsDashboardView.as_view(), name='programs_root'),

    path('directions/', TrainingDirectionListView.as_view(), name='programs_direction_list'),
    path('directions/create/', TrainingDirectionCreateView.as_view(), name='programs_direction_create'),
    path('directions/<int:pk>/', TrainingDirectionDetailView.as_view(), name='programs_direction_detail'),
    path('directions/<int:pk>/edit/', TrainingDirectionUpdateView.as_view(), name='programs_direction_update'),
    path('directions/<int:pk>/delete/', TrainingDirectionDeleteView.as_view(), name='programs_direction_delete'),

    path('profiles/', ProgramProfileListView.as_view(), name='programs_profile_list'),
    path('profiles/create/', ProgramProfileCreateView.as_view(), name='programs_profile_create'),
    path('profiles/<int:pk>/', ProgramProfileDetailView.as_view(), name='programs_profile_detail'),
    path('profiles/<int:pk>/edit/', ProgramProfileUpdateView.as_view(), name='programs_profile_update'),
    path('profiles/<int:pk>/delete/', ProgramProfileDeleteView.as_view(), name='programs_profile_delete'),

    path('educational-programs/', EducationalProgramListView.as_view(), name='programs_educational_program_list'),
    path('educational-programs/create/', EducationalProgramCreateView.as_view(), name='programs_educational_program_create'),
    path('educational-programs/<int:pk>/', EducationalProgramDetailView.as_view(), name='programs_educational_program_detail'),
    path('educational-programs/<int:pk>/edit/', EducationalProgramUpdateView.as_view(), name='programs_educational_program_update'),
    path('educational-programs/<int:pk>/delete/', EducationalProgramDeleteView.as_view(), name='programs_educational_program_delete'),

    path('profiles-by-direction/', profiles_by_direction, name='programs_profiles_by_direction'),
]
