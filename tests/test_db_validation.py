import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection

from assessment.models import AssessmentItem, AssessmentItemCompetence, AssessmentItemRow
from assessment.services import sync_assessment_item_competences
from competencies.models import Competence, DisciplineCompetence
from core.models import AssessmentItemType, CompetenceType, EducationLevel
from disciplines.models import Discipline, ProgramDiscipline
from programs.forms import EducationalProgramForm, ProgramProfileForm
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from teachers.models import Department, Teacher, TeacherProgramDiscipline


@pytest.fixture()
def validation_schema():
    if connection.vendor != 'sqlite':
        pytest.skip('Тесты form/model validation используют временную sqlite-схему.')

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


def _base_program_context():
    level = EducationLevel.objects.create(name='бакалавриат')
    direction = TrainingDirection.objects.create(
        education_level=level,
        code='09.03.02',
        name='Информационные системы и технологии',
    )
    profile = ProgramProfile.objects.create(
        training_direction=direction,
        code='09.03.02.01',
        name='Информационные системы и технологии в бизнесе',
    )
    department = Department.objects.create(
        number='1',
        short_name='ИС',
        full_name='Кафедра информационных систем',
    )
    program = EducationalProgram.objects.create(
        program_profile=profile,
        department=department,
        admission_year=2026,
    )
    return level, direction, profile, department, program


def test_program_profile_form_rejects_code_without_direction_prefix(validation_schema):
    _, direction, *_ = _base_program_context()

    form = ProgramProfileForm(data={
        'training_direction': direction.id,
        'code': '10.03.02.01',
        'name': 'Некорректный профиль',
    })

    assert form.is_valid() is False
    assert 'code' in form.errors


def test_educational_program_form_rejects_out_of_range_year(validation_schema):
    _, _, profile, department, _ = _base_program_context()

    form = EducationalProgramForm(data={
        'program_profile': profile.id,
        'department': department.id,
        'admission_year': 1999,
    })

    assert form.is_valid() is False
    assert 'admission_year' in form.errors


def test_educational_program_form_rejects_duplicate_active_program(validation_schema):
    _, _, profile, department, _ = _base_program_context()

    form = EducationalProgramForm(data={
        'program_profile': profile.id,
        'department': department.id,
        'admission_year': 2026,
    })

    assert form.is_valid() is False
    assert '__all__' in form.errors


def test_sync_assessment_item_competences_rejects_unlinked_competence(validation_schema):
    _, _, _, _, program = _base_program_context()
    discipline = Discipline.objects.create(name='Базы данных')
    program_discipline = ProgramDiscipline.objects.create(
        educational_program=program,
        discipline=discipline,
    )
    competence_type = CompetenceType.objects.create(name='ПК')
    competence = Competence.objects.create(
        educational_program=program,
        competence_type=competence_type,
        code='ПК-1',
        name='Способен работать с данными',
    )
    item_type = AssessmentItemType.objects.create(code='single', name='выбор одного ответа')
    item = AssessmentItem.objects.create(
        program_discipline=program_discipline,
        competence=None,
        assessment_item_type=item_type,
        prompt_text='Текст задания',
    )

    with pytest.raises(ValueError, match='связаны с выбранной дисциплиной'):
        sync_assessment_item_competences(item, [competence])
