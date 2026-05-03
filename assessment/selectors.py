from __future__ import annotations

from collections.abc import Iterable

from django.db.models import Q, QuerySet

from .models import AssessmentItem


def item_competence_q(competence_id) -> Q:
    return Q(competence_id=competence_id) | Q(competence_links__competence_id=competence_id)


def item_competences_q(competence_ids: Iterable[int]) -> Q:
    competence_ids = list(competence_ids)
    return Q(competence_id__in=competence_ids) | Q(competence_links__competence_id__in=competence_ids)


def filter_items_by_competence(queryset: QuerySet, competence_id) -> QuerySet:
    if not competence_id:
        return queryset
    return queryset.filter(item_competence_q(competence_id)).distinct()


def count_items_by_competence(filtered_item_ids, competence_ids: Iterable[int]) -> dict[int, int]:
    """Count distinct assessment items for each competence.

    ``AssessmentItemCompetence`` is the canonical source, but legacy rows may
    still only have ``AssessmentItem.competence_id``. Selectors must include
    both until the legacy FK is physically removed from the schema.
    """
    competence_ids = [int(value) for value in competence_ids if value is not None]
    if not competence_ids:
        return {}

    competence_ids_set = set(competence_ids)
    rows = (
        AssessmentItem.objects.filter(
            item_competences_q(competence_ids),
            id__in=filtered_item_ids,
        )
        .values('competence_id', 'competence_links__competence_id', 'id')
        .distinct()
    )

    grouped: dict[int, set[int]] = {}
    for row in rows:
        item_id = row['id']
        for competence_id in (row['competence_id'], row['competence_links__competence_id']):
            if competence_id in competence_ids_set:
                grouped.setdefault(competence_id, set()).add(item_id)
    return {competence_id: len(items) for competence_id, items in grouped.items()}


def count_items_by_program_discipline_competence(
    filtered_item_ids,
    pairs: Iterable[tuple[int, int]],
) -> dict[tuple[int, int], int]:
    pairs = [
        (int(program_discipline_id), int(competence_id))
        for program_discipline_id, competence_id in pairs
        if program_discipline_id is not None and competence_id is not None
    ]
    if not pairs:
        return {}

    program_discipline_ids = {program_discipline_id for program_discipline_id, _ in pairs}
    competence_ids = {competence_id for _, competence_id in pairs}
    pair_set = set(pairs)

    rows = (
        AssessmentItem.objects.filter(
            item_competences_q(competence_ids),
            id__in=filtered_item_ids,
            program_discipline_id__in=program_discipline_ids,
        )
        .values(
            'program_discipline_id',
            'competence_id',
            'competence_links__competence_id',
            'id',
        )
        .distinct()
    )

    grouped: dict[tuple[int, int], set[int]] = {}
    for row in rows:
        program_discipline_id = row['program_discipline_id']
        item_id = row['id']
        for competence_id in (row['competence_id'], row['competence_links__competence_id']):
            if competence_id is None:
                continue
            pair = (program_discipline_id, competence_id)
            if pair in pair_set:
                grouped.setdefault(pair, set()).add(item_id)
    return {pair: len(items) for pair, items in grouped.items()}
