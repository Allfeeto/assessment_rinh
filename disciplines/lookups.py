from __future__ import annotations

from django.db.models import Q

from assessment.access import program_discipline_queryset_for_user
from core.lookups import (
    filter_selected_id,
    register_lookup,
    tokenize_lookup_query,
    unique_lookup_results,
)
from core.permissions import filter_program_disciplines_for_assignment, is_superuser_or_platform_admin

from .models import Discipline, ProgramDiscipline


def _truthy(value):
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _lookup_mode(request):
    deleted_only = _truthy(request.GET.get('deleted_only')) or request.GET.get('mode') == 'trash'
    include_deleted = _truthy(request.GET.get('include_deleted'))
    return include_deleted, deleted_only


def _lookup_program_discipline_scope(user, *, include_deleted=False, deleted_only=False):
    return program_discipline_queryset_for_user(
        user,
        include_deleted=include_deleted,
        deleted_only=deleted_only,
    )


def _base_program_discipline_queryset(*, include_deleted=False, deleted_only=False):
    queryset = ProgramDiscipline.objects.all()
    if deleted_only:
        return queryset.filter(educational_program__is_deleted=True)
    if not include_deleted:
        return queryset.filter(educational_program__is_deleted=False)
    return queryset


def lookup_discipline(request, query, selected_id, limit):
    include_deleted, deleted_only = _lookup_mode(request)
    queryset = Discipline.objects.order_by('name')
    scoped_program_disciplines = _lookup_program_discipline_scope(
        request.user,
        include_deleted=include_deleted,
        deleted_only=deleted_only,
    )
    if not is_superuser_or_platform_admin(request.user):
        queryset = queryset.filter(program_disciplines__in=scoped_program_disciplines).distinct()
    exclude_program_id = request.GET.get('exclude_program_id')
    education_level_id = request.GET.get('education_level_id')
    training_direction_id = request.GET.get('training_direction_id')
    program_profile_id = request.GET.get('program_profile_id')
    educational_program_id = request.GET.get('educational_program_id')
    competence_id = request.GET.get('competence_id')
    if exclude_program_id:
        linked_ids = ProgramDiscipline.objects.filter(
            educational_program_id=exclude_program_id,
            educational_program__is_deleted=False,
        ).values_list('discipline_id', flat=True)
        queryset = queryset.exclude(id__in=linked_ids)
    if (
        education_level_id
        or training_direction_id
        or program_profile_id
        or educational_program_id
        or competence_id
    ):
        linked_program_disciplines = scoped_program_disciplines
        if is_superuser_or_platform_admin(request.user):
            linked_program_disciplines = _base_program_discipline_queryset(
                include_deleted=include_deleted,
                deleted_only=deleted_only,
            )
        if education_level_id:
            linked_program_disciplines = linked_program_disciplines.filter(
                educational_program__program_profile__training_direction__education_level_id=education_level_id
            )
        if training_direction_id:
            linked_program_disciplines = linked_program_disciplines.filter(
                educational_program__program_profile__training_direction_id=training_direction_id
            )
        if program_profile_id:
            linked_program_disciplines = linked_program_disciplines.filter(
                educational_program__program_profile_id=program_profile_id
            )
        if educational_program_id:
            linked_program_disciplines = linked_program_disciplines.filter(
                educational_program_id=educational_program_id
            )
        if competence_id:
            linked_program_disciplines = linked_program_disciplines.filter(
                discipline_competences__competence_id=competence_id
            )
        linked_ids = linked_program_disciplines.values_list('discipline_id', flat=True)
        queryset = queryset.filter(id__in=linked_ids)
    if query:
        tokens = tokenize_lookup_query(query) or [query.strip().lower()]
        for token in tokens:
            queryset = queryset.filter(
                Q(name__icontains=token)
                | Q(program_disciplines__discipline_code__icontains=token)
                | Q(program_disciplines__discipline_code__icontains=query.strip())
            )
    queryset = filter_selected_id(queryset, selected_id)
    label_program_disciplines = scoped_program_disciplines.select_related('discipline').order_by(
        'discipline__name',
        'discipline_code',
    )
    if educational_program_id:
        label_program_disciplines = label_program_disciplines.filter(
            educational_program_id=educational_program_id
        )
    show_discipline_name_only = request.GET.get('discipline_label') == 'name'
    labels_by_discipline_id = {}
    for program_discipline in label_program_disciplines:
        labels_by_discipline_id.setdefault(
            program_discipline.discipline_id,
            program_discipline.discipline.name
            if show_discipline_name_only
            else program_discipline.discipline_display_name,
        )
    return unique_lookup_results(
        queryset.distinct(),
        limit,
        lambda obj: labels_by_discipline_id.get(obj.id, obj.name),
    )


def lookup_program_discipline(request, query, selected_id, limit):
    include_deleted, deleted_only = _lookup_mode(request)
    queryset = _base_program_discipline_queryset(
        include_deleted=include_deleted,
        deleted_only=deleted_only,
    ).select_related(
        'educational_program__program_profile',
        'educational_program__program_profile__training_direction__education_level',
        'educational_program__department',
        'discipline',
        'department',
    ).order_by(
        'educational_program__program_profile__code',
        'educational_program__admission_year',
        'discipline__name',
    )
    if request.GET.get('purpose') == 'assignment':
        queryset = filter_program_disciplines_for_assignment(request.user, queryset)
    elif not is_superuser_or_platform_admin(request.user):
        queryset = queryset.filter(
            pk__in=_lookup_program_discipline_scope(
                request.user,
                include_deleted=include_deleted,
                deleted_only=deleted_only,
            ).values_list('id', flat=True)
        )
    educational_program_id = request.GET.get('educational_program_id')
    year = request.GET.get('admission_year') or request.GET.get('year')
    program_department_id = (
        request.GET.get('program_department_id')
        or request.GET.get('educational_program_department_id')
    )
    discipline_department_id = request.GET.get('discipline_department_id')
    if educational_program_id:
        queryset = queryset.filter(educational_program_id=educational_program_id)
    if year and str(year).isdigit():
        queryset = queryset.filter(educational_program__admission_year=int(year))
    if program_department_id and str(program_department_id).isdigit():
        queryset = queryset.filter(educational_program__department_id=int(program_department_id))
    if discipline_department_id and str(discipline_department_id).isdigit():
        queryset = queryset.filter(department_id=int(discipline_department_id))
    if query:
        tokens = tokenize_lookup_query(query) or [query.strip().lower()]
        for token in tokens:
            token_filter = (
                Q(discipline__name__icontains=token)
                | Q(discipline_code__icontains=token)
                | Q(discipline_code__icontains=query.strip())
                | Q(department__number__icontains=token)
                | Q(department__short_name__icontains=token)
                | Q(department__full_name__icontains=token)
                | Q(educational_program__program_profile__code__icontains=token)
                | Q(educational_program__program_profile__name__icontains=token)
                | Q(educational_program__department__number__icontains=token)
                | Q(educational_program__department__short_name__icontains=token)
                | Q(educational_program__department__full_name__icontains=token)
            )
            if token.isdigit() and len(token) == 4:
                token_filter |= Q(educational_program__admission_year=int(token))
            queryset = queryset.filter(token_filter)
    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(
        queryset.distinct(),
        limit,
        lambda obj: obj.discipline_display_name if educational_program_id else (
            f'{obj.educational_program.full_display_name} | '
            f'{obj.discipline_display_name}'
        ),
    )


def register_discipline_lookups() -> None:
    register_lookup('discipline', lookup_discipline)
    register_lookup('program_discipline', lookup_program_discipline)
