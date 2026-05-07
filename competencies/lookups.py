from __future__ import annotations

from assessment.access import program_discipline_queryset_for_user
from core.lookups import (
    apply_lookup_tokens,
    filter_selected_id,
    register_lookup,
    unique_lookup_results,
    user_can_lookup_all,
)

from .models import Competence, DisciplineCompetence


def _lookup_program_discipline_scope(user):
    return program_discipline_queryset_for_user(user)


def lookup_competence(request, query, selected_id, limit):
    queryset = Competence.objects.select_related(
        'educational_program__program_profile',
        'competence_type',
    ).filter(educational_program__is_deleted=False).order_by('code')
    scoped_program_disciplines = _lookup_program_discipline_scope(request.user)
    if not user_can_lookup_all(request.user):
        queryset = queryset.filter(
            educational_program__program_disciplines__in=scoped_program_disciplines,
        ).distinct()

    educational_program_id = request.GET.get('educational_program_id')
    program_discipline_id = request.GET.get('program_discipline_id')
    discipline_id = request.GET.get('discipline_id')
    education_level_id = request.GET.get('education_level_id')
    training_direction_id = request.GET.get('training_direction_id')
    program_profile_id = request.GET.get('program_profile_id')
    linked_only = request.GET.get('linked_only') in {'1', 'true', 'True'}

    if education_level_id:
        queryset = queryset.filter(
            educational_program__program_profile__training_direction__education_level_id=education_level_id
        )
    if training_direction_id:
        queryset = queryset.filter(
            educational_program__program_profile__training_direction_id=training_direction_id
        )
    if program_profile_id:
        queryset = queryset.filter(educational_program__program_profile_id=program_profile_id)

    if program_discipline_id:
        program_id = (
            scoped_program_disciplines.filter(pk=program_discipline_id)
            .filter(educational_program__is_deleted=False)
            .values_list('educational_program_id', flat=True)
            .first()
        )
        if program_id:
            queryset = queryset.filter(educational_program_id=program_id)
            if linked_only:
                linked_ids = DisciplineCompetence.objects.filter(
                    program_discipline_id=program_discipline_id
                ).values_list('competence_id', flat=True)
                queryset = queryset.filter(id__in=linked_ids)
        else:
            queryset = queryset.none()
    elif educational_program_id:
        queryset = queryset.filter(educational_program_id=educational_program_id)

    if discipline_id:
        discipline_links = DisciplineCompetence.objects.filter(
            program_discipline__discipline_id=discipline_id,
            program_discipline__educational_program__is_deleted=False,
        )
        if educational_program_id:
            discipline_links = discipline_links.filter(
                program_discipline__educational_program_id=educational_program_id
            )
        linked_ids = discipline_links.values_list('competence_id', flat=True)
        queryset = queryset.filter(id__in=linked_ids)

    if query:
        queryset = apply_lookup_tokens(queryset, query, ('code', 'name'))

    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(
        queryset.distinct(),
        limit,
        lambda obj: f'{obj.code} — {obj.name}',
        key_factory=lambda obj: (obj.code, obj.name),
    )


def register_competence_lookups() -> None:
    register_lookup('competence', lookup_competence)
