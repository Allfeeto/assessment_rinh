from __future__ import annotations

from assessment.models import AssessmentItem, AssessmentItemRow
from competencies.models import Competence, DisciplineCompetence
from disciplines.models import ProgramDiscipline


class ProgramReplaceService:
    """
    Удаляет только данные, привязанные к конкретной образовательной программе.
    Общие справочники (кафедры, дисциплины, направления и т.п.) не затрагиваются.
    """

    def delete_program_with_dependencies(self, educational_program) -> None:
        assessment_items_qs = AssessmentItem.objects.filter(
            program_discipline__educational_program=educational_program
        )
        AssessmentItemRow.objects.filter(assessment_item__in=assessment_items_qs).delete()
        assessment_items_qs.delete()

        DisciplineCompetence.objects.filter(
            program_discipline__educational_program=educational_program
        ).delete()
        ProgramDiscipline.objects.filter(educational_program=educational_program).delete()
        Competence.objects.filter(educational_program=educational_program).delete()

        educational_program.delete()

