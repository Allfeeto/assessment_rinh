import os
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from assessment.models import AssessmentItem, AssessmentItemRow
from disciplines.models import ProgramDiscipline


def _filtered_items(program_id, discipline_id, filters):
    queryset = (
        AssessmentItem.objects.select_related(
            'assessment_item_type',
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
        queryset = queryset.extra(
            where=[
                'EXISTS (SELECT 1 FROM assessment_item_competence aic '
                'WHERE aic.assessment_item_id = assessment_item.id '
                'AND aic.competence_id = %s)'
            ],
            params=[filters['competence_id']],
        )

    return queryset


def _format_item(index, item):
    lines = [f'{index}. {item.prompt_text}', f'Тип: {item.assessment_item_type.name}']
    if item.instruction_text:
        lines.append(f'Инструкция: {item.instruction_text}')

    item_type = item.assessment_item_type.name.lower()
    rows = list(item.rows.all())

    if item_type in {'single_choice', 'multiple_choice'}:
        option_rows = [row for row in rows if row.row_kind == AssessmentItemRow.KIND_OPTION]
        option_rows.sort(key=lambda row: (row.sort_order or 9999, row.id))
        for row in option_rows:
            marker = '[+]' if row.is_correct else '[ ]'
            lines.append(f'  {marker} {row.left_text or ""}')

    elif item_type == 'matching':
        if item.left_column_title or item.right_column_title:
            lines.append(
                f'  Колонки: {item.left_column_title or "Левая"} | {item.right_column_title or "Правая"}'
            )
        pair_rows = [row for row in rows if row.row_kind == AssessmentItemRow.KIND_MATCH_PAIR]
        pair_rows.sort(key=lambda row: (row.sort_order or 9999, row.id))
        for row in pair_rows:
            left_label = f'{row.left_label} ' if row.left_label else ''
            right_label = f'{row.right_label} ' if row.right_label else ''
            lines.append(
                f'  Пара: {left_label}{row.left_text or ""} -> {right_label}{row.right_text or ""}'
            )

        distractors = [
            row for row in rows if row.row_kind == AssessmentItemRow.KIND_MATCH_RIGHT_DISTRACTOR
        ]
        distractors.sort(key=lambda row: (row.sort_order or 9999, row.id))
        if distractors:
            lines.append('  Дистракторы справа:')
            for row in distractors:
                right_label = f'{row.right_label} ' if row.right_label else ''
                lines.append(f'    - {right_label}{row.right_text or ""}')

    elif item_type == 'sequence':
        sequence_rows = [row for row in rows if row.row_kind == AssessmentItemRow.KIND_SEQUENCE]
        sequence_rows.sort(key=lambda row: (row.correct_order or 9999, row.id))
        for row in sequence_rows:
            lines.append(f'  {row.correct_order}. {row.left_text or ""}')

    elif item_type == 'open_answer':
        open_rows = [row for row in rows if row.row_kind == AssessmentItemRow.KIND_OPEN_ANSWER]
        for row in open_rows:
            lines.append(f'  - {row.open_answer_text or ""}')

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