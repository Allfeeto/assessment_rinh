from __future__ import annotations

from typing import Iterable

TYPE_SINGLE = 'single'
TYPE_MULTIPLE = 'multiple'
TYPE_MATCHING = 'matching'
TYPE_SEQUENCE = 'sequence'
TYPE_OPEN = 'open'
TYPE_UNKNOWN = 'unknown'

TYPE_CODE_ALIASES = {
    TYPE_SINGLE: TYPE_SINGLE,
    TYPE_MULTIPLE: TYPE_MULTIPLE,
    TYPE_MATCHING: TYPE_MATCHING,
    TYPE_SEQUENCE: TYPE_SEQUENCE,
    TYPE_OPEN: TYPE_OPEN,
    'single_choice': TYPE_SINGLE,
    'multiple_choice': TYPE_MULTIPLE,
    'matching': TYPE_MATCHING,
    'sequence': TYPE_SEQUENCE,
    'open_answer': TYPE_OPEN,
}

TYPE_UI_LABELS = {
    TYPE_MATCHING: 'Задание закрытого типа на установление соответствия',
    TYPE_SEQUENCE: 'Задание закрытого типа на установление последовательности',
    TYPE_MULTIPLE: 'Задание закрытого типа с выбором нескольких верных ответов из предложенных',
    TYPE_SINGLE: 'Задание закрытого типа с выбором одного верного ответа из предложенных',
    TYPE_OPEN: 'Задание открытого типа с развернутым ответом',
}


def _normalize_item_type_code(value: str | None) -> str:
    normalized = (value or '').strip().lower()
    return TYPE_CODE_ALIASES.get(normalized, TYPE_UNKNOWN)


def infer_item_type_code(item_type) -> str:
    code = _normalize_item_type_code(getattr(item_type, 'code', None))
    if code != TYPE_UNKNOWN:
        return code

    value = str(getattr(item_type, 'name', item_type) or '').strip().lower()
    code = _normalize_item_type_code(value)
    if code != TYPE_UNKNOWN:
        return code

    if 'соответств' in value:
        return TYPE_MATCHING
    if 'последоват' in value:
        return TYPE_SEQUENCE
    if 'нескольк' in value:
        return TYPE_MULTIPLE
    if 'одного' in value or 'один' in value:
        return TYPE_SINGLE
    if 'открыт' in value or 'развернут' in value:
        return TYPE_OPEN

    return TYPE_UNKNOWN


def get_item_type_ui_name(item_type) -> str:
    code = infer_item_type_code(item_type)
    fallback = str(getattr(item_type, 'name', item_type) or '')
    return TYPE_UI_LABELS.get(code, fallback)


def get_ui_assessment_item_types_queryset():
    from core.models import AssessmentItemType

    return AssessmentItemType.objects.order_by('code', 'name')


def split_rows_for_detail(item_type, rows: Iterable):
    code = infer_item_type_code(item_type)
    rows_list = list(rows)

    if code in {TYPE_SINGLE, TYPE_MULTIPLE}:
        options = [row for row in rows_list if (row.left_text or '').strip()]
        options.sort(key=lambda row: (row.sort_order or 9999, row.id))
        return {
            'code': code,
            'options': options,
            'matching_pairs': [],
            'matching_distractors': [],
            'sequence_items': [],
            'open_answers': [],
        }

    if code == TYPE_MATCHING:
        pairs = [
            row
            for row in rows_list
            if (row.right_text or '').strip() and (row.left_text or '').strip()
        ]
        distractors = [
            row
            for row in rows_list
            if (row.right_text or '').strip() and not (row.left_text or '').strip()
        ]
        pairs.sort(key=lambda row: (row.sort_order or 9999, row.id))
        distractors.sort(key=lambda row: (row.sort_order or 9999, row.id))
        return {
            'code': code,
            'options': [],
            'matching_pairs': pairs,
            'matching_distractors': distractors,
            'sequence_items': [],
            'open_answers': [],
        }

    if code == TYPE_SEQUENCE:
        sequence_items = [row for row in rows_list if (row.left_text or '').strip()]
        sequence_items.sort(key=lambda row: (row.correct_order or 9999, row.id))
        return {
            'code': code,
            'options': [],
            'matching_pairs': [],
            'matching_distractors': [],
            'sequence_items': sequence_items,
            'open_answers': [],
        }

    if code == TYPE_OPEN:
        open_answers = [row for row in rows_list if (row.open_answer_text or '').strip()]
        open_answers.sort(key=lambda row: (row.sort_order or 9999, row.id))
        return {
            'code': code,
            'options': [],
            'matching_pairs': [],
            'matching_distractors': [],
            'sequence_items': [],
            'open_answers': open_answers,
        }

    return {
        'code': TYPE_UNKNOWN,
        'options': [],
        'matching_pairs': [],
        'matching_distractors': [],
        'sequence_items': [],
        'open_answers': [],
    }
