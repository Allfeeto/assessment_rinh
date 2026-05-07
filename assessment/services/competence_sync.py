from __future__ import annotations

from typing import Sequence


def get_item_competences(item) -> list:
    prefetched_links = getattr(item, '_prefetched_objects_cache', {}).get('competence_links')
    if prefetched_links is not None:
        links = [link.competence for link in prefetched_links]
    else:
        links = [link.competence for link in item.competence_links.select_related('competence').all()]

    # AssessmentItemCompetence is canonical. The legacy FK is kept in sync for
    # old schema compatibility and still has to be merged while it exists.
    if item.competence_id:
        links.append(item.competence)

    unique = {}
    for competence in links:
        if competence and competence.id not in unique:
            unique[competence.id] = competence
    return list(unique.values())


def get_item_competence_codes(item) -> str:
    competences = get_item_competences(item)
    if not competences:
        return '—'
    return ', '.join(comp.code for comp in competences)


def sync_assessment_item_competences(
    item,
    competences: Sequence,
    *,
    allow_empty: bool = False,
):
    from competencies.models import DisciplineCompetence
    from assessment.models import AssessmentItemCompetence

    unique_by_id = {}
    for competence in competences:
        if competence and competence.id not in unique_by_id:
            unique_by_id[competence.id] = competence
    selected = list(unique_by_id.values())

    if not selected and not allow_empty:
        raise ValueError('Для задания требуется минимум одна компетенция.')

    if selected and item.program_discipline_id:
        program_id = getattr(
            getattr(item, 'program_discipline', None),
            'educational_program_id',
            None,
        )
        if program_id is None:
            program_id = item.program_discipline.educational_program_id

        wrong_program_codes = [
            competence.code
            for competence in selected
            if competence.educational_program_id != program_id
        ]
        if wrong_program_codes:
            raise ValueError(
                'Компетенции должны относиться к той же образовательной программе: '
                + ', '.join(wrong_program_codes)
            )

        selected_ids = [competence.id for competence in selected]
        linked_ids = set(
            DisciplineCompetence.objects.filter(
                program_discipline_id=item.program_discipline_id,
                competence_id__in=selected_ids,
            ).values_list('competence_id', flat=True)
        )
        missing_codes = [
            competence.code
            for competence in selected
            if competence.id not in linked_ids
        ]
        if missing_codes:
            raise ValueError(
                'Компетенции должны быть связаны с выбранной дисциплиной учебного плана: '
                + ', '.join(missing_codes)
            )

    item.competence = selected[0] if selected else None
    item.save(update_fields=['competence'])

    AssessmentItemCompetence.objects.filter(assessment_item=item).delete()
    if selected:
        AssessmentItemCompetence.objects.bulk_create(
            [
                AssessmentItemCompetence(
                    assessment_item=item,
                    competence=competence,
                )
                for competence in selected
            ]
        )
