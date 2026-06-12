from __future__ import annotations

from dataclasses import dataclass

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from assessment.models import AssessmentItem, AssessmentItemCompetence, AssessmentItemRow
from competencies.models import (
    Competence,
    CompetenceIndicator,
    CompetenceIndicatorImport,
    DisciplineCompetence,
)
from disciplines.models import ProgramDiscipline
from teachers.models import TeacherProgramDiscipline

HOME_STATS_CACHE_KEY = 'core:home_stats'


@dataclass(frozen=True)
class ProgramTrashCounts:
    program_disciplines: int
    competences: int
    competence_indicators: int
    competence_indicator_imports: int
    discipline_competences: int
    assessment_items: int
    assessment_item_rows: int
    assessment_item_competences: int
    teacher_assignments: int


class ProgramTrashConflictError(ValueError):
    pass


class ProgramTrashService:
    """
    Архивирует образовательную программу целиком и выполняет физическое удаление
    только для записей, уже находящихся в корзине.
    """

    @staticmethod
    def _user_or_none(user):
        if user is not None and getattr(user, 'is_authenticated', False):
            return user
        return None

    @transaction.atomic
    def move_to_trash(self, educational_program, *, user=None, reason=None):
        if educational_program.is_deleted:
            return educational_program

        educational_program.is_deleted = True
        educational_program.deleted_at = timezone.now()
        educational_program.deleted_by = self._user_or_none(user)
        educational_program.delete_reason = reason or ''
        educational_program.save(
            update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'delete_reason']
        )
        cache.delete(HOME_STATS_CACHE_KEY)
        return educational_program

    def get_counts(self, educational_program) -> ProgramTrashCounts:
        program_disciplines = ProgramDiscipline.objects.filter(
            educational_program=educational_program
        )
        assessment_items = AssessmentItem.objects.filter(
            program_discipline__educational_program=educational_program
        )
        return ProgramTrashCounts(
            program_disciplines=program_disciplines.count(),
            competences=Competence.objects.filter(educational_program=educational_program).count(),
            competence_indicators=CompetenceIndicator.objects.filter(
                competence__educational_program=educational_program,
            ).count(),
            competence_indicator_imports=CompetenceIndicatorImport.objects.filter(
                educational_program=educational_program,
            ).count(),
            discipline_competences=DisciplineCompetence.objects.filter(
                program_discipline__educational_program=educational_program
            ).count(),
            assessment_items=assessment_items.count(),
            assessment_item_rows=AssessmentItemRow.objects.filter(
                assessment_item__in=assessment_items
            ).count(),
            assessment_item_competences=AssessmentItemCompetence.objects.filter(
                assessment_item__in=assessment_items
            ).count(),
            teacher_assignments=TeacherProgramDiscipline.objects.filter(
                program_discipline__in=program_disciplines
            ).count(),
        )

    @transaction.atomic
    def restore_from_trash(self, educational_program, *, user=None):
        if not educational_program.is_deleted:
            return educational_program

        conflict = educational_program.__class__.objects.active().filter(
            program_profile=educational_program.program_profile,
            department=educational_program.department,
            admission_year=educational_program.admission_year,
        ).exclude(pk=educational_program.pk).exists()
        if conflict:
            raise ProgramTrashConflictError(
                'Нельзя восстановить программу, потому что уже существует активная '
                'образовательная программа с тем же профилем, кафедрой и годом набора.'
            )

        educational_program.is_deleted = False
        educational_program.deleted_at = None
        educational_program.deleted_by = None
        educational_program.delete_reason = None
        educational_program.save(
            update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'delete_reason']
        )
        cache.delete(HOME_STATS_CACHE_KEY)
        return educational_program

    @transaction.atomic
    def hard_delete(self, educational_program) -> None:
        if not educational_program.is_deleted:
            raise ValueError('Окончательно удалить можно только программу из корзины.')

        program_disciplines = ProgramDiscipline.objects.filter(
            educational_program=educational_program
        )
        assessment_items = AssessmentItem.objects.filter(
            program_discipline__in=program_disciplines
        )

        TeacherProgramDiscipline.objects.filter(program_discipline__in=program_disciplines).delete()
        AssessmentItemCompetence.objects.filter(assessment_item__in=assessment_items).delete()
        AssessmentItemRow.objects.filter(assessment_item__in=assessment_items).delete()
        assessment_items.delete()
        DisciplineCompetence.objects.filter(program_discipline__in=program_disciplines).delete()
        CompetenceIndicator.objects.filter(
            competence__educational_program=educational_program,
        ).delete()
        program_disciplines.delete()
        Competence.objects.filter(educational_program=educational_program).delete()
        CompetenceIndicatorImport.objects.filter(educational_program=educational_program).delete()
        educational_program.delete()
        cache.delete(HOME_STATS_CACHE_KEY)
