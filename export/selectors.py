from __future__ import annotations

import re

from assessment.models import AssessmentItem
from assessment.selectors import filter_items_by_competence
from disciplines.models import ProgramDiscipline

INVALID_FILENAME_CHARS_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')
WHITESPACE_RE = re.compile(r'\s+')


def filtered_items(program_id, discipline_id, filters):
    queryset = (
        AssessmentItem.objects.select_related(
            'assessment_item_type',
            'competence',
            'program_discipline__discipline',
            'program_discipline__educational_program__program_profile',
        )
        .prefetch_related('rows')
        .filter(
            program_discipline__educational_program_id=program_id,
            program_discipline__educational_program__is_deleted=False,
            program_discipline__discipline_id=discipline_id,
        )
        .order_by('id')
    )

    if filters.get('assessment_item_type_id'):
        queryset = queryset.filter(assessment_item_type_id=filters['assessment_item_type_id'])

    if filters.get('competence_id'):
        queryset = filter_items_by_competence(queryset, filters['competence_id'])

    return queryset.prefetch_related('competence_links__competence').distinct()


def get_program_discipline_for_export(
    program_id,
    discipline_id,
    *,
    program_discipline_model=ProgramDiscipline,
):
    return (
        program_discipline_model.objects.select_related(
            'educational_program__program_profile',
            'discipline',
        )
        .filter(
            educational_program_id=program_id,
            educational_program__is_deleted=False,
            discipline_id=discipline_id,
        )
        .first()
    )


def _sanitize_filename_part(value, fallback: str) -> str:
    text = str(value or '').strip()
    text = INVALID_FILENAME_CHARS_RE.sub(' ', text)
    text = WHITESPACE_RE.sub(' ', text).strip(' ._')
    return text or fallback


def _get_program_code(program) -> str:
    profile = getattr(program, 'program_profile', None)
    return getattr(profile, 'code', None) or getattr(program, 'code', None) or ''


def build_export_filename(program, discipline) -> str:
    program_fallback = f'program_{getattr(program, "id", "unknown")}'
    discipline_fallback = f'discipline_{getattr(discipline, "id", "unknown")}'
    program_code = _sanitize_filename_part(_get_program_code(program), program_fallback)
    discipline_name = _sanitize_filename_part(getattr(discipline, 'name', None), discipline_fallback)
    return f'{program_code}_{discipline_name}.docx'
