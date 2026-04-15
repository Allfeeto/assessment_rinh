from __future__ import annotations

from typing import Iterable

TYPE_SINGLE = 'single'
TYPE_MULTIPLE = 'multiple'
TYPE_MATCHING = 'matching'
TYPE_SEQUENCE = 'sequence'
TYPE_OPEN = 'open'
TYPE_UNKNOWN = 'unknown'

TYPE_UI_LABELS = {
    TYPE_MATCHING: 'Задание закрытого типа на установление соответствия',
    TYPE_SEQUENCE: 'Задание закрытого типа на установление последовательности',
    TYPE_MULTIPLE: 'Задание закрытого типа с выбором нескольких верных ответов из предложенных',
    TYPE_SINGLE: 'Задание закрытого типа с выбором одного верного ответа из предложенных',
    TYPE_OPEN: 'Задание открытого типа с развернутым ответом',
}


def infer_item_type_code(type_name: str | None) -> str:
    value = (type_name or '').strip().lower()

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


def get_item_type_ui_name(type_name: str | None) -> str:
    code = infer_item_type_code(type_name)
    return TYPE_UI_LABELS.get(code, type_name or '')


def get_ui_assessment_item_types_queryset():
    from core.models import AssessmentItemType

    ui_qs = AssessmentItemType.objects.filter(name__istartswith='Задание').order_by('name')
    return ui_qs if ui_qs.exists() else AssessmentItemType.objects.order_by('name')


def split_rows_for_detail(type_name: str | None, rows: Iterable):
    code = infer_item_type_code(type_name)
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


def prettify_db_error(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return 'Не удалось сохранить данные. Проверьте заполнение формы.'

    first_line = message.splitlines()[0].strip()
    first_lower = first_line.lower()

    if 'assessment_item.program_discipline_id и assessment_item.competence_id' in first_lower:
        return 'Дисциплина учебного плана и компетенция задания должны относиться к одной образовательной программе.'
    if 'отсутствует связь program_discipline -> competence' in first_lower:
        return 'Для выбранной дисциплины учебного плана нет связи с этой компетенцией в матрице дисциплина-компетенция.'
    if 'заведующий кафедрой должен относиться к той же кафедре' in first_lower:
        return 'Заведующий кафедрой должен быть преподавателем этой же кафедры.'
    if 'должны принадлежать одному educational_program' in first_lower:
        return 'Выбраны данные из разных образовательных программ. Проверьте выбранные значения.'
    if 'неизвестный тип задания' in first_lower:
        return (
            'Не удалось сопоставить тип задания для сохранения. '
            'Проверьте тип задания и повторите попытку.'
        )

    return first_line
