import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection

from assessment.models import AssessmentItem, AssessmentItemCompetence, AssessmentItemRow
from competencies.models import Competence, DisciplineCompetence
from core.models import AcademicDegree, AcademicTitle, AssessmentItemType, CompetenceType, EducationLevel
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from programs.services import PlxConflictError, PlxImportError, PlxImportService, PlxProgramUpdateService
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
        AcademicDegree,
        AcademicTitle,
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
    old_program = EducationalProgram.objects.get(pk=first_result.created_program_id)
    assert old_program.is_deleted is True
    assert not EducationalProgram.objects.active().filter(pk=first_result.created_program_id).exists()

    program = EducationalProgram.objects.get(pk=replacement_result.created_program_id)
    assert program.is_deleted is False
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


def test_import_stores_program_discipline_code_and_department(import_schema):
    service = PlxImportService()
    dto = _dto(
        discipline_names=['Анализ данных'],
        competence_codes=['ПК-1'],
        links=[(1, 1)],
    )
    dto.disciplines[0].code = 'Б1.О.07'
    dto.disciplines[0].department_code = '22'
    dto.disciplines[0].department = DepartmentInfoDTO(
        number='22',
        short_name='ИСиПИ',
        full_name='Информационных систем и прикладной информатики',
    )

    result = service.import_program(dto, replace_existing=False)

    program_discipline = ProgramDiscipline.objects.select_related('department').get(
        educational_program_id=result.created_program_id,
        discipline__name='Анализ данных',
    )
    assert program_discipline.discipline_code == 'Б1.О.07'
    assert program_discipline.department.number == '22'
    assert program_discipline.department.short_name == 'ИСиПИ'


def test_repeated_discipline_name_keeps_first_program_discipline_metadata(import_schema):
    service = PlxImportService()
    dto = _dto(
        discipline_names=['Производственная практика', 'Производственная практика'],
        competence_codes=['ПК-1', 'ПК-2'],
        links=[(1, 1), (2, 2)],
    )
    dto.disciplines[0].code = 'Б2.В.01'
    dto.disciplines[1].code = 'Б2.В.02'

    result = service.import_program(dto, replace_existing=False)

    program_disciplines = list(
        ProgramDiscipline.objects.filter(
            educational_program_id=result.created_program_id,
            discipline__name='Производственная практика',
        )
    )
    assert len(program_disciplines) == 1
    assert program_disciplines[0].discipline_code == 'Б2.В.01'
    assert DisciplineCompetence.objects.filter(
        program_discipline=program_disciplines[0],
    ).count() == 2


def test_import_duplicate_discipline_code_is_rejected(import_schema):
    service = PlxImportService()
    dto = _dto(
        discipline_names=['Первая дисциплина', 'Вторая дисциплина'],
        competence_codes=['ПК-1'],
        links=[(1, 1)],
    )
    dto.disciplines[0].code = 'Б1.О.07'
    dto.disciplines[1].code = 'Б1.О.07'

    with pytest.raises(PlxImportError):
        service.import_program(dto, replace_existing=False)


def test_update_preview_does_not_change_database(import_schema):
    import_service = PlxImportService()
    update_service = PlxProgramUpdateService(import_service=import_service)
    first_dto = _dto(
        discipline_names=['Анализ данных'],
        competence_codes=['ПК-1'],
        links=[(1, 1)],
    )
    first_dto.disciplines[0].code = 'Б1.О.07'
    result = import_service.import_program(first_dto, replace_existing=False)
    program = EducationalProgram.objects.get(pk=result.created_program_id)

    update_dto = _dto(
        discipline_names=['Анализ данных', 'Визуализация данных'],
        competence_codes=['ПК-1', 'ПК-2'],
        links=[(1, 1), (2, 2)],
    )
    update_dto.disciplines[0].code = 'Б1.О.07'
    update_dto.disciplines[1].code = 'Б1.О.08'

    preview = update_service.build_preview(update_dto, program)

    assert preview.can_apply is True
    assert [entry.label for entry in preview.additions['disciplines']] == [
        'Б1.О.08 — Визуализация данных'
    ]
    assert ProgramDiscipline.objects.filter(educational_program=program).count() == 1
    assert Competence.objects.filter(educational_program=program).count() == 1


def test_update_existing_program_preserves_assignments_and_items(import_schema):
    import_service = PlxImportService()
    update_service = PlxProgramUpdateService(import_service=import_service)
    first_dto = _dto(
        discipline_names=['Анализ данных'],
        competence_codes=['ПК-1'],
        links=[(1, 1)],
    )
    first_dto.disciplines[0].code = 'Б1.О.07'
    first_result = import_service.import_program(first_dto, replace_existing=False)
    program = EducationalProgram.objects.get(pk=first_result.created_program_id)
    program_discipline = ProgramDiscipline.objects.get(
        educational_program=program,
        discipline_code='Б1.О.07',
    )
    teacher = Teacher.objects.create(
        department=program.department,
        full_name='Иванов Иван Иванович',
    )
    teacher_assignment = TeacherProgramDiscipline.objects.create(
        teacher=teacher,
        program_discipline=program_discipline,
    )
    item_type = AssessmentItemType.objects.create(code='single', name='выбор одного ответа')
    assessment_item = AssessmentItem.objects.create(
        program_discipline=program_discipline,
        competence=Competence.objects.get(educational_program=program, code='ПК-1'),
        assessment_item_type=item_type,
        prompt_text='Текст задания',
    )

    update_dto = _dto(
        discipline_names=['Анализ данных и визуализация', 'Хранилища данных'],
        competence_codes=['ПК-1', 'ПК-2'],
        links=[(1, 1), (2, 2)],
    )
    update_dto.disciplines[0].code = 'Б1.О.07'
    update_dto.disciplines[0].department_code = '22'
    update_dto.disciplines[0].department = DepartmentInfoDTO(
        number='22',
        short_name='АД',
        full_name='Кафедра анализа данных',
    )
    update_dto.disciplines[1].code = 'Б1.О.08'

    update_result = update_service.apply_update(update_dto, program)

    program_discipline.refresh_from_db()
    assert update_result.created_disciplines == 1
    assert update_result.updated_disciplines == 1
    assert program_discipline.id == teacher_assignment.program_discipline_id
    assert program_discipline.id == assessment_item.program_discipline_id
    assert program_discipline.discipline.name == 'Анализ данных и визуализация'
    assert program_discipline.department.number == '22'
    assert ProgramDiscipline.objects.filter(educational_program=program).count() == 2
    assert TeacherProgramDiscipline.objects.filter(
        pk=teacher_assignment.pk,
        program_discipline=program_discipline,
    ).exists()
    assert AssessmentItem.objects.filter(
        pk=assessment_item.pk,
        program_discipline=program_discipline,
    ).exists()


def test_update_marks_missing_discipline_inactive_without_deleting_assignments(import_schema):
    import_service = PlxImportService()
    update_service = PlxProgramUpdateService(import_service=import_service)
    first_dto = _dto(
        discipline_names=['Анализ данных', 'Старые системы'],
        competence_codes=['ПК-1', 'ПК-2'],
        links=[(1, 1), (2, 2)],
    )
    first_dto.disciplines[0].code = 'Б1.О.07'
    first_dto.disciplines[1].code = 'Б1.О.09'
    first_result = import_service.import_program(first_dto, replace_existing=False)
    program = EducationalProgram.objects.get(pk=first_result.created_program_id)
    missing_program_discipline = ProgramDiscipline.objects.get(
        educational_program=program,
        discipline_code='Б1.О.09',
    )
    teacher = Teacher.objects.create(
        department=program.department,
        full_name='Петров Петр Петрович',
    )
    assignment = TeacherProgramDiscipline.objects.create(
        teacher=teacher,
        program_discipline=missing_program_discipline,
    )

    update_dto = _dto(
        discipline_names=['Анализ данных'],
        competence_codes=['ПК-1'],
        links=[(1, 1)],
    )
    update_dto.disciplines[0].code = 'Б1.О.07'

    preview = update_service.build_preview(update_dto, program)
    update_result = update_service.apply_update(update_dto, program)

    missing_program_discipline.refresh_from_db()
    assert update_result.marked_inactive_disciplines == 1
    assert missing_program_discipline.is_active_in_plan is False
    assert TeacherProgramDiscipline.objects.filter(pk=assignment.pk).exists()
    assert preview.conflicts
    assert any('не будет удалена' in conflict.message for conflict in preview.conflicts)


def test_update_duplicate_discipline_code_blocks_apply(import_schema):
    import_service = PlxImportService()
    update_service = PlxProgramUpdateService(import_service=import_service)
    first_dto = _dto(
        discipline_names=['Анализ данных'],
        competence_codes=['ПК-1'],
        links=[(1, 1)],
    )
    first_dto.disciplines[0].code = 'Б1.О.07'
    first_result = import_service.import_program(first_dto, replace_existing=False)
    program = EducationalProgram.objects.get(pk=first_result.created_program_id)

    update_dto = _dto(
        discipline_names=['Анализ данных', 'Другая дисциплина'],
        competence_codes=['ПК-1'],
        links=[(1, 1)],
    )
    update_dto.disciplines[0].code = 'Б1.О.07'
    update_dto.disciplines[1].code = 'Б1.О.07'

    preview = update_service.build_preview(update_dto, program)

    assert preview.has_blocking_conflicts is True
    with pytest.raises(PlxImportError):
        update_service.apply_update(update_dto, program)
