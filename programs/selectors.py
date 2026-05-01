from __future__ import annotations

from assessment.models import AssessmentItem
from competencies.models import Competence, DisciplineCompetence
from disciplines.models import ProgramDiscipline
from teachers.models import TeacherProgramDiscipline

from .models import EducationalProgram


def active_programs():
    return EducationalProgram.objects.active()


def trash_programs():
    return EducationalProgram.objects.in_trash()


def active_program_disciplines():
    return ProgramDiscipline.objects.filter(educational_program__is_deleted=False)


def trash_program_disciplines():
    return ProgramDiscipline.objects.filter(educational_program__is_deleted=True)


def active_competences():
    return Competence.objects.filter(educational_program__is_deleted=False)


def trash_competences():
    return Competence.objects.filter(educational_program__is_deleted=True)


def active_discipline_competences():
    return DisciplineCompetence.objects.filter(
        program_discipline__educational_program__is_deleted=False
    )


def active_assessment_items():
    return AssessmentItem.objects.filter(
        program_discipline__educational_program__is_deleted=False
    )


def trash_assessment_items():
    return AssessmentItem.objects.filter(
        program_discipline__educational_program__is_deleted=True
    )


def active_teacher_program_disciplines():
    return TeacherProgramDiscipline.objects.filter(
        program_discipline__educational_program__is_deleted=False
    )
