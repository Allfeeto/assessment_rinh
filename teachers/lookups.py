from __future__ import annotations

from core.lookups import (
    apply_lookup_tokens,
    filter_selected_id,
    register_lookup,
    unique_lookup_results,
    user_can_lookup_all,
)

from .models import Department, Teacher


def lookup_department(request, query, selected_id, limit):
    queryset = Department.objects.order_by('number')
    if not user_can_lookup_all(request.user):
        teacher = getattr(request.user, 'teacher_profile', None)
        queryset = queryset.filter(pk=teacher.department_id) if teacher else queryset.none()
    if query:
        queryset = apply_lookup_tokens(queryset, query, ('number', 'short_name', 'full_name'))
    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(
        queryset,
        limit,
        lambda obj: f'{obj.number} — {obj.short_name}',
    )


def lookup_teacher(request, query, selected_id, limit):
    queryset = Teacher.objects.select_related('department').order_by('full_name')
    if not user_can_lookup_all(request.user):
        teacher = getattr(request.user, 'teacher_profile', None)
        queryset = queryset.filter(pk=teacher.pk) if teacher else queryset.none()
    department_id = request.GET.get('department_id')
    if department_id:
        queryset = queryset.filter(department_id=department_id)
    if query:
        queryset = apply_lookup_tokens(
            queryset,
            query,
            ('full_name', 'department__number', 'department__short_name'),
        )
    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(
        queryset,
        limit,
        lambda obj: f'{obj.full_name} ({obj.department.short_name})',
    )


def register_teacher_lookups() -> None:
    register_lookup('department', lookup_department)
    register_lookup('teacher', lookup_teacher)
