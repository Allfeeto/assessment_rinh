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

from .models import EducationalProgram, ProgramProfile, TrainingDirection


def _lookup_program_discipline_scope(user):
    return program_discipline_queryset_for_user(user)


def _lookup_program_discipline_ids(user):
    return _lookup_program_discipline_scope(user).values_list('id', flat=True)


def lookup_training_direction(request, query, selected_id, limit):
    queryset = TrainingDirection.objects.order_by('code')
    if not user_can_lookup_all(request.user):
        queryset = queryset.filter(
            program_profiles__educational_programs__program_disciplines__id__in=(
                _lookup_program_discipline_ids(request.user)
            ),
        ).distinct()
    education_level_id = request.GET.get('education_level_id')
    if education_level_id:
        queryset = queryset.filter(education_level_id=education_level_id)
    if query:
        queryset = apply_lookup_tokens(queryset, query, ('code', 'name'))
    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(
        queryset,
        limit,
        lambda obj: f'{obj.code} — {obj.name}',
    )


def lookup_program_profile(request, query, selected_id, limit):
    queryset = ProgramProfile.objects.select_related('training_direction').order_by('code')
    if not user_can_lookup_all(request.user):
        queryset = queryset.filter(
            educational_programs__program_disciplines__id__in=_lookup_program_discipline_ids(request.user),
        ).distinct()
    direction_id = request.GET.get('training_direction_id')
    education_level_id = request.GET.get('education_level_id')
    if education_level_id:
        queryset = queryset.filter(training_direction__education_level_id=education_level_id)
    if direction_id:
        queryset = queryset.filter(training_direction_id=direction_id)
    if query:
        queryset = apply_lookup_tokens(
            queryset,
            query,
            ('code', 'name', 'training_direction__code', 'training_direction__name'),
        )
    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(
        queryset,
        limit,
        lambda obj: f'{obj.code} — {obj.name} ({obj.training_direction.code})',
    )


def lookup_educational_program(request, query, selected_id, limit):
    queryset = EducationalProgram.objects.active().select_related(
        'program_profile__training_direction',
        'department',
    ).order_by('program_profile__code', 'admission_year')
    if not user_can_lookup_all(request.user):
        queryset = queryset.filter(
            program_disciplines__id__in=_lookup_program_discipline_ids(request.user),
        ).distinct()
    education_level_id = request.GET.get('education_level_id')
    training_direction_id = request.GET.get('training_direction_id')
    program_profile_id = request.GET.get('program_profile_id')
    discipline_id = request.GET.get('discipline_id')
    competence_id = request.GET.get('competence_id')
    if education_level_id:
        queryset = queryset.filter(
            program_profile__training_direction__education_level_id=education_level_id
        )
    if training_direction_id:
        queryset = queryset.filter(program_profile__training_direction_id=training_direction_id)
    if program_profile_id:
        queryset = queryset.filter(program_profile_id=program_profile_id)
    if discipline_id:
        queryset = queryset.filter(program_disciplines__discipline_id=discipline_id)
    if competence_id:
        queryset = queryset.filter(competences__id=competence_id)
    if query:
        tokens = tokenize_lookup_query(query) or [query.strip().lower()]
        for token in tokens:
            token_filter = (
                Q(program_profile__code__icontains=token)
                | Q(program_profile__name__icontains=token)
                | Q(program_profile__training_direction__code__icontains=token)
                | Q(program_profile__training_direction__name__icontains=token)
                | Q(department__number__icontains=token)
                | Q(department__short_name__icontains=token)
                | Q(department__full_name__icontains=token)
            )
            if token.isdigit() and len(token) == 4:
                token_filter |= Q(admission_year=int(token))
            queryset = queryset.filter(token_filter)
    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(queryset.distinct(), limit, str)


def register_program_lookups() -> None:
    register_lookup('training_direction', lookup_training_direction)
    register_lookup('program_profile', lookup_program_profile)
    register_lookup('educational_program', lookup_educational_program)
