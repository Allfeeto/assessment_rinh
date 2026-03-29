import os
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from assessment.forms import normalize_item_type_name
from assessment.models import AssessmentItem
from disciplines.models import ProgramDiscipline


def _build_queryset(program_id, discipline_id, filters):
    queryset = (
        AssessmentItem.objects.select_related(
            'program_discipline__educational_program',
            'program_discipline__discipline',
            'assessment_item_type',
        )
        .prefetch_related('options', 'matching_left_items', 'sequence_items', 'open_answers')
        .filter(
            program_discipline__educational_program_id=program_id,
            program_discipline__discipline_id=discipline_id,
        )
        .order_by('id')
    )

    assessment_item_type_id = filters.get('assessment_item_type')
    if assessment_item_type_id:
        queryset = queryset.filter(assessment_item_type_id=assessment_item_type_id)

    competence_id = filters.get('competence')
    if competence_id:
        queryset = queryset.extra(
            where=[
                'EXISTS (SELECT 1 FROM assessment_item_competence aic '
                'WHERE aic.assessment_item_id = assessment_item.id '
                'AND aic.competence_id = %s)'
            ],
            params=[competence_id],
        )

    return queryset


def _format_assessment_item(index, item):
    lines = [f'{index}. {item.text}', f'Тип задания: {item.assessment_item_type.name}']
    item_type_name = normalize_item_type_name(item.assessment_item_type.name)

    if item_type_name in {'один', 'несколько'}:
        for option in item.options.order_by('sort_order', 'id'):
            marker = '[+]' if option.is_correct else '[ ]'
            lines.append(f'  {marker} {option.sort_order}. {option.text}')

    elif item_type_name == 'соответствие':
        for left_item in item.matching_left_items.order_by('sort_order', 'id'):
            right_item = left_item.matched_answer.right_item if hasattr(left_item, 'matched_answer') else None
            right_repr = f'{right_item.label}) {right_item.text}' if right_item else 'не задано'
            lines.append(f'  {left_item.label}) {left_item.text} -> {right_repr}')

    elif item_type_name == 'последовательность':
        for sequence_item in item.sequence_items.order_by('correct_order', 'id'):
            lines.append(f'  {sequence_item.correct_order}. {sequence_item.text}')

    elif item_type_name == 'открытый':
        for open_answer in item.open_answers.order_by('id'):
            lines.append(f'  - {open_answer.text}')

    return '\n'.join(lines)


def generate_docx(program_id, discipline_id, filters):
    from docx import Document
    from docxtpl import DocxTemplate

    program_discipline = (
        ProgramDiscipline.objects.select_related('educational_program', 'discipline')
        .filter(
            educational_program_id=program_id,
            discipline_id=discipline_id,
        )
        .first()
    )
    if not program_discipline:
        raise ValueError('Связка программы и дисциплины не найдена.')

    queryset = _build_queryset(program_id, discipline_id, filters)

    body = '\n\n'.join(
        _format_assessment_item(index, item)
        for index, item in enumerate(queryset, start=1)
    )
    if not body:
        body = 'По выбранным фильтрам задания не найдены.'

    template_fd, template_name = tempfile.mkstemp(suffix='.docx')
    os.close(template_fd)
    Path(template_name).unlink(missing_ok=True)

    template_document = Document()
    template_document.add_heading('Оценочные материалы', level=1)
    template_document.add_paragraph('Программа: {{ program_name }}')
    template_document.add_paragraph('Дисциплина: {{ discipline_name }}')
    template_document.add_paragraph('Дата формирования: {{ generated_at }}')
    template_document.add_paragraph('{{ body }}')
    template_document.save(template_name)

    doc_template = DocxTemplate(template_name)
    doc_template.render(
        {
            'program_name': f'{program_discipline.educational_program.code} {program_discipline.educational_program.name}',
            'discipline_name': program_discipline.discipline.name,
            'generated_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'body': body,
        }
    )

    output = BytesIO()
    doc_template.save(output)
    output.seek(0)

    Path(template_name).unlink(missing_ok=True)

    return output.getvalue()
