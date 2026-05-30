from __future__ import annotations

from django.db.models import Q

from assessment.access import program_discipline_queryset_for_user
from core.lookups import (
    apply_lookup_tokens,
    filter_selected_id,
    register_lookup,
    tokenize_lookup_query,
    unique_lookup_results,
    user_can_lookup_all,
)

from .models import Discipline, ProgramDiscipline


def _lookup_program_discipline_scope(user):
    return program_discipline_queryset_for_user(user)


def _lookup_program_discipline_ids(user):
    return _lookup_program_discipline_scope(user).values_list('id', flat=True)


def lookup_discipline(request, query, selected_id, limit):
    queryset = Discipline.objects.order_by('name')
    scoped_program_disciplines = _lookup_program_discipline_scope(request.user)
    if not user_can_lookup_all(request.user):
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
        if user_can_lookup_all(request.user):
            linked_program_disciplines = ProgramDiscipline.objects.filter(
                educational_program__is_deleted=False
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
        queryset = apply_lookup_tokens(queryset, query, ('name',))
    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(queryset.distinct(), limit, lambda obj: obj.name)


def lookup_program_discipline(request, query, selected_id, limit):
    queryset = ProgramDiscipline.objects.select_related(
        'educational_program__program_profile',
        'educational_program__department',
        'discipline',
        'department',
    ).filter(educational_program__is_deleted=False).order_by(
        'educational_program__program_profile__code',
        'educational_program__admission_year',
        'discipline__name',
    )
    if not user_can_lookup_all(request.user):
        queryset = queryset.filter(pk__in=_lookup_program_discipline_ids(request.user))
    educational_program_id = request.GET.get('educational_program_id')
    if educational_program_id:
        queryset = queryset.filter(educational_program_id=educational_program_id)
    if query:
        tokens = tokenize_lookup_query(query) or [query.strip().lower()]
        for token in tokens:
            token_filter = (
                Q(discipline__name__icontains=token)
                | Q(discipline_code__icontains=token)
                | Q(department__number__icontains=token)
                | Q(department__short_name__icontains=token)
                | Q(educational_program__program_profile__code__icontains=token)
                | Q(educational_program__program_profile__name__icontains=token)
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
        lambda obj: (
            f'{obj.educational_program} | '
            f'{f"{obj.discipline_code} - " if obj.discipline_code else ""}'
            f'{obj.discipline.name}'
        ),
    )


def register_discipline_lookups() -> None:
    register_lookup('discipline', lookup_discipline)
    register_lookup('program_discipline', lookup_program_discipline)
