import os
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from assessment.models import AssessmentItem
from assessment.services import (
    TYPE_MATCHING,
    TYPE_MULTIPLE,
    TYPE_OPEN,
    TYPE_SEQUENCE,
    TYPE_SINGLE,
    get_item_type_ui_name,
    infer_item_type_code,
)
from disciplines.models import ProgramDiscipline

RUS_LETTERS = ['А', 'Б', 'В', 'Г', 'Д', 'Е', 'Ж', 'З', 'И', 'К', 'Л', 'М', 'Н', 'О', 'П', 'Р', 'С', 'Т']


def _letter(index):
    if 0 <= index < len(RUS_LETTERS):
        return RUS_LETTERS[index]
    return str(index + 1)


def _filtered_items(program_id, discipline_id, filters):
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
            program_discipline__discipline_id=discipline_id,
        )
        .order_by('id')
    )

    if filters.get('assessment_item_type_id'):
        queryset = queryset.filter(assessment_item_type_id=filters['assessment_item_type_id'])

    if filters.get('competence_id'):
        queryset = queryset.filter(competence_id=filters['competence_id'])

    return queryset


def _format_choice(rows):
    prepared = [row for row in rows if (row.left_text or '').strip()]
    prepared.sort(key=lambda row: (row.sort_order or 9999, row.id))

    lines = []
    for index, row in enumerate(prepared):
        marker = '[+]' if row.is_correct else '[ ]'
        lines.append(f'  {_letter(index)}. {marker} {row.left_text or ""}')
    return lines


def _format_matching(item, rows):
    rows_sorted = sorted(rows, key=lambda row: (row.sort_order or 9999, row.id))
    pairs = [row for row in rows_sorted if (row.left_text or '').strip() and (row.right_text or '').strip()]
    distractors = [row for row in rows_sorted if not (row.left_text or '').strip() and (row.right_text or '').strip()]

    right_items = [pair.right_text for pair in pairs] + [row.right_text for row in distractors]
    right_index = {text: idx + 1 for idx, text in enumerate(right_items)}

    lines = []
    if item.left_column_title or item.right_column_title:
        lines.append(
            f'  Колонки: {item.left_column_title or "Левая"} | {item.right_column_title or "Правая"}'
        )

    lines.append('  Левая колонка:')
    for index, pair in enumerate(pairs):
        lines.append(f'    {_letter(index)}. {pair.left_text}')

    lines.append('  Правая колонка:')
    for idx, text in enumerate(right_items, start=1):
        lines.append(f'    {idx}. {text}')

    if pairs:
        lines.append('  Ключ:')
        for index, pair in enumerate(pairs):
            lines.append(f'    {_letter(index)} -> {right_index.get(pair.right_text, "?")}')

    return lines


def _format_sequence(rows):
    prepared = [row for row in rows if (row.left_text or '').strip()]
    prepared.sort(key=lambda row: (row.correct_order or 9999, row.id))
    return [f'  {row.correct_order}. {row.left_text}' for row in prepared]


def _format_open(rows):
    prepared = [row for row in rows if (row.open_answer_text or '').strip()]
    prepared.sort(key=lambda row: (row.sort_order or 9999, row.id))
    return [f'  - {row.open_answer_text}' for row in prepared]


def _format_item(index, item):
    lines = [
        f'{index}. {item.prompt_text}',
        f'Тип: {get_item_type_ui_name(item.assessment_item_type.name)}',
        f'Компетенция: {item.competence.code} — {item.competence.name}',
    ]
    if item.instruction_text:
        lines.append(f'Инструкция: {item.instruction_text}')

    rows = list(item.rows.all())
    item_type_code = infer_item_type_code(item.assessment_item_type.name)

    if item_type_code in {TYPE_SINGLE, TYPE_MULTIPLE}:
        lines.extend(_format_choice(rows))
    elif item_type_code == TYPE_MATCHING:
        lines.extend(_format_matching(item, rows))
    elif item_type_code == TYPE_SEQUENCE:
        lines.extend(_format_sequence(rows))
    elif item_type_code == TYPE_OPEN:
        lines.extend(_format_open(rows))

    return '\n'.join(lines)


def generate_docx(program_id, discipline_id, filters):
    from docx import Document
    from docxtpl import DocxTemplate

    program_discipline = (
        ProgramDiscipline.objects.select_related('educational_program__program_profile', 'discipline')
        .filter(educational_program_id=program_id, discipline_id=discipline_id)
        .first()
    )

    if not program_discipline:
        raise ValueError('Связка программы и дисциплины не найдена.')

    items = _filtered_items(program_id, discipline_id, filters)
    body = '\n\n'.join(_format_item(index, item) for index, item in enumerate(items, start=1))
    if not body:
        body = 'По выбранным фильтрам задания не найдены.'

    fd, template_path = tempfile.mkstemp(suffix='.docx')
    os.close(fd)
    Path(template_path).unlink(missing_ok=True)

    template = Document()
    template.add_heading('Оценочные материалы', level=1)
    template.add_paragraph('Программа: {{ program_name }}')
    template.add_paragraph('Дисциплина: {{ discipline_name }}')
    template.add_paragraph('Дата: {{ generated_at }}')
    template.add_paragraph('{{ content }}')
    template.save(template_path)

    doc = DocxTemplate(template_path)
    doc.render(
        {
            'program_name': str(program_discipline.educational_program),
            'discipline_name': program_discipline.discipline.name,
            'generated_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'content': body,
        }
    )

    out = BytesIO()
    doc.save(out)
    out.seek(0)
    Path(template_path).unlink(missing_ok=True)
    return out.getvalue()
