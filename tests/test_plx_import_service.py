import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection

from assessment.models import AssessmentItem, AssessmentItemCompetence, AssessmentItemRow
from competencies.models import Competence, DisciplineCompetence
from core.models import AssessmentItemType, CompetenceType, EducationLevel
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from programs.services import PlxConflictError, PlxImportService
from programs.services.plx_dto import (
    CompetenceDTO,
    DepartmentInfoDTO,
    DisciplineCompetenceLinkDTO,
    DisciplineDTO,
    PlxProgramImportDTO,
    ProgramInfoDTO,
)
from teachers.models import Department, Teacher, TeacherProgramDiscipline


@pytest.fixture()
def import_schema():
    if connection.vendor != 'sqlite':
        pytest.skip('Интеграционный тест импорта создаёт временную схему только в sqlite.')

    models = [
        ContentType,
        Permission,
        Group,
        User,
        EducationLevel,
        CompetenceType,
        AssessmentItemType,
        Department,
        Teacher,
        TrainingDirection,
        ProgramProfile,
        EducationalProgram,
        Discipline,
        ProgramDiscipline,
        Competence,
        DisciplineCompetence,
        TeacherProgramDiscipline,
        AssessmentItem,
        AssessmentItemRow,
        AssessmentItemCompetence,
    ]

    with connection.schema_editor() as schema_editor:
        for model in models:
            schema_editor.create_model(model)

    yield

    with connection.schema_editor() as schema_editor:
        for model in reversed(models):
            schema_editor.delete_model(model)


def _dto(*, discipline_names, competence_codes, links):
    disciplines = [
        DisciplineDTO(external_id=f'discipline-{index}', code='', name=name)
        for index, name in enumerate(discipline_names, start=1)
    ]
    competences = [
        CompetenceDTO(
            external_id=f'competence-{index}',
            code=code,
            name=f'Компетенция {code}',
            competence_type_name=code.split('-', 1)[0],
        )
        for index, code in enumerate(competence_codes, start=1)
    ]
    return PlxProgramImportDTO(
        source_filename='test.plx',
        program=ProgramInfoDTO(
            education_level_name='бакалавриат',
            training_direction_code='99.03.02',
            training_direction_name='Тестовое направление',
            profile_code='99.03.02.01',
            profile_name='Тестовый профиль',
            admission_year=2099,
        ),
        department=DepartmentInfoDTO(
            number='999',
            short_name='ТЕСТ',
            full_name='Тестовая кафедра',
        ),
        disciplines=disciplines,
        competences=competences,
        discipline_competence_links=[
            DisciplineCompetenceLinkDTO(
                discipline_external_id=f'discipline-{discipline_index}',
                competence_external_id=f'competence-{competence_index}',
            )
            for discipline_index, competence_index in links
        ],
    )


def test_import_existing_program_requires_confirm_and_replace_recreates_relations(import_schema):
    service = PlxImportService()
    first_dto = _dto(
        discipline_names=['Первая дисциплина', 'Вторая дисциплина'],
        competence_codes=['ПК-1', 'ПК-2'],
        links=[(1, 1), (2, 2)],
    )

    first_result = service.import_program(first_dto, replace_existing=False)

    with pytest.raises(PlxConflictError):
        service.import_program(first_dto, replace_existing=False)

    replacement_dto = _dto(
        discipline_names=['Новая дисциплина'],
        competence_codes=['ПК-3', 'ПК-4'],
        links=[(1, 1), (1, 2)],
    )
    replacement_result = service.import_program(replacement_dto, replace_existing=True)

    assert replacement_result.replaced_program_id == first_result.created_program_id
    assert replacement_result.created_program_id != first_result.created_program_id
    assert not EducationalProgram.objects.filter(pk=first_result.created_program_id).exists()

    program = EducationalProgram.objects.get(pk=replacement_result.created_program_id)
    assert list(program.program_disciplines.values_list('discipline__name', flat=True)) == [
        'Новая дисциплина'
    ]
    assert list(program.competences.order_by('code').values_list('code', flat=True)) == ['ПК-3', 'ПК-4']
    assert list(
        DisciplineCompetence.objects.filter(
            program_discipline__educational_program=program,
        )
        .order_by('competence__code')
        .values_list('program_discipline__discipline__name', 'competence__code')
    ) == [
        ('Новая дисциплина', 'ПК-3'),
        ('Новая дисциплина', 'ПК-4'),
    ]
