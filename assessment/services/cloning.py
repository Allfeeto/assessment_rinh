from __future__ import annotations

from .competence_sync import get_item_competences, sync_assessment_item_competences


def clone_assessment_item_to_program_discipline(source_item, target_program_discipline):
    from competencies.models import DisciplineCompetence
    from assessment.models import AssessmentItem, AssessmentItemRow

    if target_program_discipline.educational_program.is_deleted:
        raise ValueError('Нельзя вставлять задания в образовательную программу из корзины.')

    source_competences = get_item_competences(source_item)
    target_links = (
        DisciplineCompetence.objects.filter(program_discipline=target_program_discipline)
        .select_related('competence__competence_type')
        .order_by('competence__code', 'competence_id')
    )
    target_by_key = {}
    for link in target_links:
        competence = link.competence
        code_key = (competence.code or '').strip().lower()
        type_id = competence.competence_type_id
        type_name = (getattr(competence.competence_type, 'name', '') or '').strip().lower()
        target_by_key.setdefault((code_key, type_id), competence)
        target_by_key.setdefault((code_key, type_name), competence)

    transferable_competences = []
    seen_target_ids = set()
    for source_competence in source_competences:
        code_key = (source_competence.code or '').strip().lower()
        type_id = source_competence.competence_type_id
        type_name = (getattr(source_competence.competence_type, 'name', '') or '').strip().lower()
        target_competence = target_by_key.get((code_key, type_id)) or target_by_key.get((code_key, type_name))
        if target_competence and target_competence.id not in seen_target_ids:
            seen_target_ids.add(target_competence.id)
            transferable_competences.append(target_competence)

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
