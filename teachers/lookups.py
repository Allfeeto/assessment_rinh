from __future__ import annotations

from django.db.models import Q

from core.lookups import (
    apply_lookup_tokens,
    filter_selected_id,
    register_lookup,
    unique_lookup_results,
    user_can_lookup_all,
)
from core.permissions import (
    filter_teachers_for_assignment,
    get_user_departments,
    is_senior_teacher,
    is_superuser_or_platform_admin,
)

from .models import Department, Teacher


def lookup_department(request, query, selected_id, limit):
    queryset = Department.objects.order_by('number')
    purpose = request.GET.get('purpose')
    if purpose in {'teacher_management', 'program_discipline_management'}:
        queryset = get_user_departments(request.user).order_by('number')
    elif not user_can_lookup_all(request.user):
        teacher = getattr(request.user, 'teacher_profile', None)
        queryset = (
            queryset.filter(
                Q(pk=teacher.department_id) | Q(teachers_by_membership=teacher)
            ).distinct()
            if teacher
            else queryset.none()
        )
    if query:
        queryset = apply_lookup_tokens(queryset, query, ('number', 'short_name', 'full_name'))
    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(
        queryset,
        limit,
        lambda obj: f'{obj.number} — {obj.short_name}',
    )


def lookup_teacher(request, query, selected_id, limit):
    queryset = Teacher.objects.select_related('department').prefetch_related('departments').order_by('full_name')
    if request.GET.get('purpose') == 'assignment':
        queryset = filter_teachers_for_assignment(request.user, queryset)
    elif is_senior_teacher(request.user) and not is_superuser_or_platform_admin(request.user):
        queryset = filter_teachers_for_assignment(request.user, queryset)
    elif not user_can_lookup_all(request.user):
        teacher = getattr(request.user, 'teacher_profile', None)
        queryset = queryset.filter(pk=teacher.pk) if teacher else queryset.none()
    department_id = request.GET.get('department_id')
    if department_id:
        queryset = queryset.filter(
            Q(department_id=department_id) | Q(departments__id=department_id)
        ).distinct()
    if query:
        queryset = apply_lookup_tokens(
            queryset,
            query,
            (
                'full_name',
                'department__number',
                'department__short_name',
                'departments__number',
                'departments__short_name',
            ),
        )
    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(
        queryset,
        limit,
        lambda obj: f'{obj.full_name} ({obj.departments_display})',
    )


def register_teacher_lookups() -> None:
    register_lookup('department', lookup_department)
    register_lookup('teacher', lookup_teacher)
