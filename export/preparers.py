from __future__ import annotations

import logging
import random

from assessment.services import (
    TYPE_MATCHING,
    TYPE_MULTIPLE,
    TYPE_OPEN,
    TYPE_SEQUENCE,
    TYPE_SINGLE,
    get_item_competences,
    get_item_type_ui_name,
    infer_item_type_code,
)

from .errors import WordExportError

RUS_LETTERS = ['А', 'Б', 'В', 'Г', 'Д', 'Е', 'Ж', 'З', 'И', 'К', 'Л', 'М', 'Н', 'О', 'П', 'Р', 'С', 'Т']
logger = logging.getLogger(__name__)

ANSWER_INSTRUCTION_BY_TYPE = {
    TYPE_MATCHING: 'Запишите выбранные цифры под соответствующими буквами, каждый элемент правого столбца используется один раз:',
    TYPE_SEQUENCE: 'Запишите соответствующую последовательность цифр слева направо:',
    TYPE_MULTIPLE: 'Варианты ответа.',
    TYPE_SINGLE: 'Вариант ответа.',
    TYPE_OPEN: 'Укажите правильный ответ:',
}

TASK_INTRO_BY_TYPE = {
    TYPE_MATCHING: 'Прочитайте текст и установите соответствие.',
    TYPE_SEQUENCE: 'Прочитайте текст и установите последовательность.',
    TYPE_MULTIPLE: 'Прочитайте текст, выберите все правильные варианты ответа.',
    TYPE_SINGLE: 'Прочитайте текст и выберите правильный ответ.',
    TYPE_OPEN: 'Прочитайте текст и запишите ответ.',
}

CRITERIA_BY_TYPE = {
    TYPE_MATCHING: (
        '1 балл – полное совпадение с верным ответом; '
        '0 баллов – неверный ответ или его отсутствие.'
    ),
    TYPE_SEQUENCE: (
        '1 балл – полное совпадение с верным ответом; '
        '0 баллов – если допущены ошибки или ответ отсутствует.'
    ),
    TYPE_MULTIPLE: (
        '1 балл – полное совпадение с верным ответом; '
        '0 баллов – неверный ответ или его отсутствие.'
    ),
    TYPE_SINGLE: (
        '1 балл – полное совпадение с верным ответом; '
        '0 баллов – допущены ошибки или ответ отсутствует.'
    ),
    TYPE_OPEN: (
        '2 балла – полный правильный ответ на задание / полное совпадение с эталоном ответа; '
        '1 балл – допущена одна ошибка / неточность / ответ правильный, но не полный; '
        '0 баллов – допущено более одной ошибки / ответ неправильный / ответ отсутствует.'
    ),
}


def _letter(index: int) -> str:
    if 0 <= index < len(RUS_LETTERS):
        return RUS_LETTERS[index]
    return str(index + 1)


def _cleanup_text(value):
    return (value or '').strip()


def _normalize_sort_text(value) -> str:
    return str(value or '').strip().casefold()


def _iter_rows(item):
    return list(item.rows.order_by('sort_order', 'id'))


def _resolve_indicators_text(item) -> str:
    return '—'


def _competence_sort_tuple(competence):
    return (
        _normalize_sort_text(getattr(competence, 'code', '')),
        _normalize_sort_text(getattr(competence, 'name', '')),
        getattr(competence, 'id', 0) or 0,
    )


def _get_export_competences(item) -> list:
    competences = list(get_item_competences(item))
    primary = getattr(item, 'competence', None)
    primary_id = getattr(item, 'competence_id', None) or getattr(primary, 'id', None)

    unique = {}
    for competence in competences:
        if not competence:
            continue
        competence_id = getattr(competence, 'id', None)
        key = competence_id if competence_id is not None else id(competence)
        unique[key] = competence

    if primary:
        primary_key = primary_id if primary_id is not None else id(primary)
        unique.setdefault(primary_key, primary)
    else:
        primary_key = None

    primary_competence = unique.pop(primary_key, None) if primary_key is not None else None
    ordered = sorted(unique.values(), key=_competence_sort_tuple)
    if primary_competence:
        return [primary_competence, *ordered]
    return ordered


def _format_competences_text(competences: list) -> str:
    return '; '.join(
        f'{competence.code} — {competence.name}'
        for competence in competences
    ) or '—'


def get_item_competence_sort_key(item):
    competences = _get_export_competences(item)
    if not competences:
        return (1, '', '', 0)
    return (0, *_competence_sort_tuple(competences[0]))


def _get_item_type_sort_key(item):
    item_type = getattr(item, 'assessment_item_type', None)
    type_name = get_item_type_ui_name(item_type)
    type_code = infer_item_type_code(item_type)
    type_id = getattr(item, 'assessment_item_type_id', None) or getattr(item_type, 'id', 0) or 0
    return (_normalize_sort_text(type_name), _normalize_sort_text(type_code), type_id)


def sort_assessment_items(items):
    return sorted(
        items,
        key=lambda item: (
            get_item_competence_sort_key(item),
            _get_item_type_sort_key(item),
            getattr(item, 'id', 0) or 0,
        ),
    )


def _prepare_matching_rows(rows, rng: random.Random):
    pairs = []
    distractors = []

    for row in rows:
        left = _cleanup_text(row.left_text)
        right = _cleanup_text(row.right_text)
        if not right:
            continue
        data = {'id': row.id, 'left': left, 'right': right}
        if left:
            pairs.append(data)
        else:
            distractors.append(data)

    right_items = [{'id': pair['id'], 'text': pair['right']} for pair in pairs]
    right_items.extend({'id': row['id'], 'text': row['right']} for row in distractors)
    rng.shuffle(right_items)
    right_index = {entry['id']: idx + 1 for idx, entry in enumerate(right_items)}

    letters = [_letter(i) for i in range(len(pairs))]
    key_parts = [f'{letters[idx]}-{right_index[pair["id"]]}' for idx, pair in enumerate(pairs)]

    return {
        'pairs': pairs,
        'right_items': right_items,
        'letters': letters,
        'answer_key': ', '.join(key_parts),
    }


def _prepare_sequence_rows(rows, rng: random.Random):
    source_rows = [row for row in rows if _cleanup_text(row.left_text)]
    source_rows.sort(key=lambda row: (row.sort_order or 9999, row.id))

    steps = []
    for index, row in enumerate(source_rows, start=1):
        correct_order = row.correct_order if row.correct_order is not None else index
        steps.append({'id': row.id, 'text': _cleanup_text(row.left_text), 'correct_order': correct_order})

    rng.shuffle(steps)
    visible_index = {step['id']: idx + 1 for idx, step in enumerate(steps)}
    correct_chain = sorted(steps, key=lambda step: step['correct_order'])
    answer_key = ', '.join(str(visible_index[step['id']]) for step in correct_chain)
    return {
        'steps': steps,
        'answer_cells': max(len(steps), 1),
        'answer_key': answer_key,
    }


def _list_item_text(index: int, text: str, is_last: bool) -> str:
    suffix = '.' if is_last else ';'
    normalized = (text or '').strip().rstrip(' ;:,.')
    return f'{index}) {normalized}{suffix}'


def _prepare_choice_rows(rows, rng: random.Random, multiple: bool):
    options = [
        {'id': row.id, 'text': _cleanup_text(row.left_text), 'is_correct': bool(row.is_correct)}
        for row in rows
        if _cleanup_text(row.left_text)
    ]
    rng.shuffle(options)

    correct_positions = [idx + 1 for idx, option in enumerate(options) if option['is_correct']]
    if multiple:
        answer_key = ', '.join(str(position) for position in correct_positions)
    else:
        answer_key = str(correct_positions[0]) if correct_positions else ''

    return {
        'options': options,
        'answer_key': answer_key,
    }


def _prepare_open_rows(rows):
    answers = [_cleanup_text(row.open_answer_text) for row in rows if _cleanup_text(row.open_answer_text)]
    return {
        'answers': answers,
        'answer_key': '; '.join(answers),
    }


def _prepare_export_item(item, number: int, rng: random.Random):
    rows = _iter_rows(item)
    type_name = get_item_type_ui_name(item.assessment_item_type)
    type_code = infer_item_type_code(item.assessment_item_type)

    if type_code not in {TYPE_MATCHING, TYPE_SEQUENCE, TYPE_MULTIPLE, TYPE_SINGLE, TYPE_OPEN}:
        logger.warning(
            'Unsupported assessment item type during Word export',
            extra={
                'assessment_item_id': item.id,
                'assessment_item_type_id': item.assessment_item_type_id,
                'assessment_item_type_name': item.assessment_item_type.name,
            },
        )
        raise WordExportError(
            'В выбранном наборе есть задания с неподдерживаемым типом. '
            'Проверьте типы заданий и повторите экспорт.'
        )

    competences = _get_export_competences(item)
    prepared = {
        'number': number,
        'item': item,
        'type_name': type_name,
        'type_code': type_code,
        'task_intro': TASK_INTRO_BY_TYPE.get(type_code, ''),
        'prompt_text': _cleanup_text(item.prompt_text),
        'criteria': CRITERIA_BY_TYPE.get(type_code, ''),
        'answer_instruction': ANSWER_INSTRUCTION_BY_TYPE.get(type_code, ''),
        'indicator_text': _resolve_indicators_text(item),
        'answer_key': '',
        'payload': {},
        'competence_text': _format_competences_text(competences),
        'competence_sort_key': get_item_competence_sort_key(item),
        'type_sort_key': _get_item_type_sort_key(item),
    }

    if type_code == TYPE_MATCHING:
        payload = _prepare_matching_rows(rows, rng)
        prepared['payload'] = payload
        prepared['answer_key'] = payload['answer_key']
    elif type_code == TYPE_SEQUENCE:
        payload = _prepare_sequence_rows(rows, rng)
        prepared['payload'] = payload
        prepared['answer_key'] = payload['answer_key']
    elif type_code == TYPE_MULTIPLE:
        payload = _prepare_choice_rows(rows, rng, multiple=True)
        prepared['payload'] = payload
        prepared['answer_key'] = payload['answer_key']
    elif type_code == TYPE_SINGLE:
        payload = _prepare_choice_rows(rows, rng, multiple=False)
        prepared['payload'] = payload
        prepared['answer_key'] = payload['answer_key']
    elif type_code == TYPE_OPEN:
        payload = _prepare_open_rows(rows)
        prepared['payload'] = payload
        prepared['answer_key'] = payload['answer_key']

    return prepared


def build_numbered_items(items, rng: random.Random):
    return [
        _prepare_export_item(item, number=index, rng=rng)
        for index, item in enumerate(sort_assessment_items(items), start=1)
    ]


def build_specification_groups(prepared_items: list[dict]) -> list[dict]:
    groups = {}
    for prepared in prepared_items:
        key = (
            prepared['competence_text'],
            prepared['indicator_text'],
            prepared['type_name'],
        )
        group = groups.setdefault(
            key,
            {
                'competence_text': prepared['competence_text'],
                'indicator_text': prepared['indicator_text'],
                'type_name': prepared['type_name'],
                'numbers': [],
                'competence_sort_key': prepared.get(
                    'competence_sort_key',
                    (0, _normalize_sort_text(prepared['competence_text']), '', 0),
                ),
                'type_sort_key': prepared.get(
                    'type_sort_key',
                    (_normalize_sort_text(prepared['type_name']), '', 0),
                ),
            },
        )
        group['numbers'].append(prepared['number'])

    result = []
    for group in groups.values():
        numbers = sorted(group['numbers'])
        result.append(
            {
                **group,
                'numbers': numbers,
                'numbers_text': ', '.join(str(number) for number in numbers),
                'first_number': numbers[0],
            }
        )

    return sorted(
        result,
        key=lambda group: (
            group['competence_sort_key'],
            _normalize_sort_text(group['indicator_text']),
            group['type_sort_key'],
            group['first_number'],
        ),
    )
