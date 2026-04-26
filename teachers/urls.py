from django.urls import path

from .views import (
    DepartmentCreateView,
    DepartmentDeleteView,
    DepartmentDetailView,
    DepartmentListView,
    DepartmentUpdateView,
    TeacherAssignmentPanelView,
    TeacherAssignmentToggleView,
    TeacherCreateView,
    TeacherDeleteView,
    TeacherDetailView,
    TeacherListView,
    TeacherProgramDisciplineCreateView,
    TeacherProgramDisciplineDeleteView,
    TeacherProgramDisciplineDetailView,
    TeacherProgramDisciplineListView,
    TeacherProgramDisciplineUpdateView,
    TeacherUpdateView,
    TeachersDashboardView,
)

urlpatterns = [
    path('', TeachersDashboardView.as_view(), name='teachers_root'),

    path(
        'assignments/panel/',
        TeacherAssignmentPanelView.as_view(),
        name='teachers_assignments_panel',
    ),
    path(
        'assignments/toggle/',
        TeacherAssignmentToggleView.as_view(),
        name='teachers_assignments_toggle',
    ),

    path('departments/', DepartmentListView.as_view(), name='teachers_department_list'),
    path('departments/create/', DepartmentCreateView.as_view(), name='teachers_department_create'),
    path('departments/<int:pk>/', DepartmentDetailView.as_view(), name='teachers_department_detail'),
    path('departments/<int:pk>/edit/', DepartmentUpdateView.as_view(), name='teachers_department_update'),
    path('departments/<int:pk>/delete/', DepartmentDeleteView.as_view(), name='teachers_department_delete'),

    path('teachers/', TeacherListView.as_view(), name='teachers_teacher_list'),
    path('teachers/create/', TeacherCreateView.as_view(), name='teachers_teacher_create'),
    path('teachers/<int:pk>/', TeacherDetailView.as_view(), name='teachers_teacher_detail'),
    path('teachers/<int:pk>/edit/', TeacherUpdateView.as_view(), name='teachers_teacher_update'),
    path('teachers/<int:pk>/delete/', TeacherDeleteView.as_view(), name='teachers_teacher_delete'),

    path(
        'teacher-program-disciplines/',
        TeacherProgramDisciplineListView.as_view(),
        name='teachers_teacher_program_discipline_list',
    ),
    path(
        'teacher-program-disciplines/create/',
        TeacherProgramDisciplineCreateView.as_view(),
        name='teachers_teacher_program_discipline_create',
    ),
    path(
        'teacher-program-disciplines/<int:pk>/',
        TeacherProgramDisciplineDetailView.as_view(),
        name='teachers_teacher_program_discipline_detail',
    ),
    path(
        'teacher-program-disciplines/<int:pk>/edit/',
        TeacherProgramDisciplineUpdateView.as_view(),
        name='teachers_teacher_program_discipline_update',
    ),
    path(
        'teacher-program-disciplines/<int:pk>/delete/',
        TeacherProgramDisciplineDeleteView.as_view(),
        name='teachers_teacher_program_discipline_delete',
    ),
]
