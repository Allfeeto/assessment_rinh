from __future__ import annotations

from typing import Iterable, Sequence

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
CLIPBOARD_SESSION_KEY = 'assessment_clipboard_item_ids'


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


def get_item_competences(item) -> list:
    prefetched_links = getattr(item, '_prefetched_objects_cache', {}).get('competence_links')
    if prefetched_links is not None:
        links = [link.competence for link in prefetched_links]
    else:
        links = [link.competence for link in item.competence_links.select_related('competence').all()]
    if not links and item.competence_id:
        links = [item.competence]

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
    from .models import AssessmentItemCompetence

    unique_by_id = {}
    for competence in competences:
        if competence and competence.id not in unique_by_id:
            unique_by_id[competence.id] = competence
    selected = list(unique_by_id.values())

    if not selected and not allow_empty:
        raise ValueError('Для задания требуется минимум одна компетенция.')

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


def get_clipboard_item_ids(session) -> list[int]:
    raw = session.get(CLIPBOARD_SESSION_KEY, [])
    result = []
    for value in raw:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return result


def set_clipboard_item_ids(session, item_ids: Sequence[int]) -> None:
    unique_ids = []
    seen = set()
    for value in item_ids:
        try:
            item_id = int(value)
        except (TypeError, ValueError):
            continue
        if item_id not in seen:
            seen.add(item_id)
            unique_ids.append(item_id)
    session[CLIPBOARD_SESSION_KEY] = unique_ids
    session.modified = True


def clear_clipboard(session) -> None:
    if CLIPBOARD_SESSION_KEY in session:
        del session[CLIPBOARD_SESSION_KEY]
        session.modified = True


def clone_assessment_item_to_program_discipline(source_item, target_program_discipline):
    from competencies.models import Competence, DisciplineCompetence
    from .models import AssessmentItem, AssessmentItemRow

    source_competences = get_item_competences(source_item)
    source_competence_ids = [competence.id for competence in source_competences]

    allowed_competence_ids = list(
        DisciplineCompetence.objects.filter(
            program_discipline=target_program_discipline,
            competence_id__in=source_competence_ids,
        ).values_list('competence_id', flat=True)
    )
    allowed_set = set(allowed_competence_ids)
    ordered_allowed_ids = [comp_id for comp_id in source_competence_ids if comp_id in allowed_set]
    competence_map = {
        competence.id: competence
        for competence in Competence.objects.filter(id__in=ordered_allowed_ids)
    }
    transferable_competences = [
        competence_map[comp_id]
        for comp_id in ordered_allowed_ids
        if comp_id in competence_map
    ]

    new_item = AssessmentItem.objects.create(
        program_discipline=target_program_discipline,
        competence=transferable_competences[0] if transferable_competences else None,
        assessment_item_type=source_item.assessment_item_type,
        prompt_text=source_item.prompt_text,
        left_column_title=source_item.left_column_title,
        right_column_title=source_item.right_column_title,
    )

    source_rows = list(source_item.rows.order_by('sort_order', 'id'))
    AssessmentItemRow.objects.bulk_create(
        [
            AssessmentItemRow(
                assessment_item=new_item,
                left_text=row.left_text,
                right_text=row.right_text,
                sort_order=row.sort_order,
                correct_order=row.correct_order,
                is_correct=row.is_correct,
                open_answer_text=row.open_answer_text,
            )
            for row in source_rows
        ]
    )

    sync_assessment_item_competences(
        new_item,
        transferable_competences,
        allow_empty=True,
    )
    return new_item, transferable_competences
