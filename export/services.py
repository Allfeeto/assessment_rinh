from __future__ import annotations

import logging
import random
from datetime import datetime
from io import BytesIO

from disciplines.models import ProgramDiscipline

from .docx_renderer import MAKET_PATH, build_document as _build_document
from .errors import WordExportError, WordExportNotFoundError
from .preparers import (
    _prepare_export_item,
    build_specification_groups,
    sort_assessment_items,
)
from .selectors import (
    build_export_filename,
    filtered_items as _select_filtered_items,
    get_program_discipline_for_export,
)

MAX_EXPORT_ITEMS = 1000
logger = logging.getLogger(__name__)


def _filtered_items(program_id, discipline_id, filters):
    return _select_filtered_items(program_id, discipline_id, filters)


def _get_program_discipline(program_id, discipline_id):
    return get_program_discipline_for_export(
        program_id,
        discipline_id,
        program_discipline_model=ProgramDiscipline,
    )


def _build_seed(program_id, discipline_id, items_count, *, seed=None, now=None) -> str:
    if seed is not None:
        return str(seed)

    current_time = now() if callable(now) else now
    if current_time is None:
        current_time = datetime.now()
    return f'{program_id}:{discipline_id}:{items_count}:{current_time.strftime("%Y%m%d%H%M%S%f")}'


def build_numbered_items(items, rng: random.Random):
    return [
        _prepare_export_item(item, number=index, rng=rng)
        for index, item in enumerate(sort_assessment_items(items), start=1)
    ]


def generate_docx(program_id, discipline_id, filters, *, seed=None, now=None):
    program_discipline = _get_program_discipline(program_id, discipline_id)
    if not program_discipline:
        raise WordExportNotFoundError('Связка активной программы и дисциплины не найдена.')

    items_queryset = _filtered_items(program_id, discipline_id, filters)
    items_count = items_queryset.count()
    if items_count > MAX_EXPORT_ITEMS:
        logger.info(
            'Word export item limit exceeded',
            extra={
                'program_id': program_id,
                'discipline_id': discipline_id,
                'items_count': items_count,
                'max_export_items': MAX_EXPORT_ITEMS,
            },
        )
        raise WordExportError(
            f'В экспорт попало слишком много заданий: {items_count}. '
            f'Уточните фильтры, максимум за один экспорт — {MAX_EXPORT_ITEMS}.'
        )

    items = list(items_queryset)
    if not items:
        raise WordExportNotFoundError('По выбранным фильтрам задания не найдены.')

    rng = random.Random(
        _build_seed(program_id, discipline_id, len(items), seed=seed, now=now)
    )
    prepared_items = build_numbered_items(items, rng=rng)
    doc = _build_document(program_discipline, prepared_items)

    out = BytesIO()
    doc.save(out)
    out.seek(0)
    return out.getvalue()
