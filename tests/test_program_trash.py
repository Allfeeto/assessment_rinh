import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.db import connection
from django.test import Client, override_settings
from django.urls import reverse

from assessment.access import allowed_program_discipline_ids_for_user, can_access_program_discipline
from assessment.models import AssessmentItem, AssessmentItemCompetence, AssessmentItemRow
from assessment.services import clone_assessment_item_to_program_discipline
from competencies.models import (
    Competence,
    CompetenceIndicator,
    CompetenceIndicatorImport,
    DisciplineCompetence,
)
from core.permissions import SENIOR_TEACHER_GROUP_NAME
from core.models import AcademicDegree, AcademicTitle, AssessmentItemType, CompetenceType, EducationLevel
from disciplines.models import Discipline, ProgramDiscipline
from export.services import WordExportNotFoundError, generate_docx
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from programs.services.program_trash_service import ProgramTrashConflictError, ProgramTrashService
from teachers.models import Department, Teacher, TeacherProgramDiscipline


@pytest.fixture()
def trash_schema():
    if connection.vendor != 'sqlite':
        pytest.skip('Тесты корзины создают временную схему только в sqlite.')

    models = [
        ContentType,
        Permission,
        Group,
        User,
        Session,
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
        CompetenceIndicatorImport,
        CompetenceIndicator,
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


def _base_refs():
    level = EducationLevel.objects.create(name='Бакалавриат')
    direction = TrainingDirection.objects.create(
        education_level=level,
        code='99.03.01',
        name='Тестовое направление',
    )
    profile = ProgramProfile.objects.create(
        training_direction=direction,
        code='99.03.01.01',
        name='Тестовый профиль',
    )
    department = Department.objects.create(
        number='999',
        short_name='ТЕСТ',
        full_name='Тестовая кафедра',
    )
    competence_type = CompetenceType.objects.create(name='ПК')
    item_type = AssessmentItemType.objects.create(code='single', name='Один ответ')
    discipline = Discipline.objects.create(name='Тестовая дисциплина')
    return profile, department, competence_type, item_type, discipline


def _program_bundle(*, year=2099, competence_code='ПК-1', prompt='Старое задание'):
    profile, department, competence_type, item_type, discipline = _base_refs()
    program = EducationalProgram.objects.create(
        program_profile=profile,
        department=department,
        admission_year=year,
    )
    program_discipline = ProgramDiscipline.objects.create(
        educational_program=program,
        discipline=discipline,
    )
    competence = Competence.objects.create(
        educational_program=program,
        competence_type=competence_type,
        code=competence_code,
        name='Компетенция 1',
    )
    DisciplineCompetence.objects.create(
        program_discipline=program_discipline,
        competence=competence,
    )
    indicator_import = CompetenceIndicatorImport.objects.create(
        educational_program=program,
        source_filename='indicators.doc',
        source_sha256='a' * 64,
        status=CompetenceIndicatorImport.Status.COMPLETED,
    )
    indicator = CompetenceIndicator.objects.create(
        competence=competence,
        last_import=indicator_import,
        code=f'{competence_code}.1',
        text='Знает тестовые основы',
        source_file='indicators.doc',
        source_table_number=1,
        source_row_number=2,
    )
    item = AssessmentItem.objects.create(
        program_discipline=program_discipline,
        competence=competence,
        assessment_item_type=item_type,
        prompt_text=prompt,
    )
    AssessmentItemRow.objects.create(
        assessment_item=item,
        left_text='A',
        sort_order=1,
        is_correct=True,
    )
    AssessmentItemCompetence.objects.create(
        assessment_item=item,
        competence=competence,
    )
    user = User.objects.create_user(username=f'teacher-{year}')
    teacher = Teacher.objects.create(
        user=user,
        department=department,
        full_name='Иванов И.И.',
    )
    TeacherProgramDiscipline.objects.create(
        teacher=teacher,
        program_discipline=program_discipline,
    )
    return {
        'program': program,
        'program_discipline': program_discipline,
        'competence': competence,
        'indicator': indicator,
        'indicator_import': indicator_import,
        'item': item,
        'discipline': discipline,
        'item_type': item_type,
        'competence_type': competence_type,
        'teacher_user': user,
        'department': department,
        'profile': profile,
    }


def test_soft_delete_keeps_related_data(trash_schema):
    data = _program_bundle()
    service = ProgramTrashService()

    service.move_to_trash(data['program'], user=data['teacher_user'], reason='test')

    data['program'].refresh_from_db()
    assert data['program'].is_deleted is True
    assert data['program'].deleted_by == data['teacher_user']
    assert ProgramDiscipline.objects.filter(pk=data['program_discipline'].pk).exists()
    assert Competence.objects.filter(pk=data['competence'].pk).exists()
    assert CompetenceIndicator.objects.filter(pk=data['indicator'].pk).exists()
    assert CompetenceIndicatorImport.objects.filter(pk=data['indicator_import'].pk).exists()
    assert DisciplineCompetence.objects.filter(program_discipline=data['program_discipline']).exists()
    assert AssessmentItem.objects.filter(pk=data['item'].pk).exists()
    assert AssessmentItemRow.objects.filter(assessment_item=data['item']).exists()
    assert AssessmentItemCompetence.objects.filter(assessment_item=data['item']).exists()
    assert TeacherProgramDiscipline.objects.filter(program_discipline=data['program_discipline']).exists()


def test_active_querysets_and_teacher_scope_exclude_trash_by_default(trash_schema):
    data = _program_bundle()
    ProgramTrashService().move_to_trash(data['program'], user=data['teacher_user'])

    assert list(EducationalProgram.objects.active()) == []
    assert list(EducationalProgram.objects.in_trash()) == [data['program']]
    assert allowed_program_discipline_ids_for_user(data['teacher_user']) == []
    assert allowed_program_discipline_ids_for_user(data['teacher_user'], deleted_only=True) == [
        data['program_discipline'].id
    ]


@override_settings(ALLOWED_HOSTS=['testserver'])
def test_senior_teacher_group_without_teacher_profile_has_no_department_scope(trash_schema):
    data = _program_bundle()
    senior = User.objects.create_user(username='senior-without-profile')
    senior.groups.add(Group.objects.create(name=SENIOR_TEACHER_GROUP_NAME))

    assert allowed_program_discipline_ids_for_user(senior) == []
    assert can_access_program_discipline(senior, data['program_discipline'].id) is False

    client = Client()
    client.force_login(senior)
    response = client.get(reverse('assessment_workspace'))

    assert response.status_code == 302


def test_export_for_trash_program_is_blocked(trash_schema):
    data = _program_bundle()
    ProgramTrashService().move_to_trash(data['program'], user=data['teacher_user'])

    with pytest.raises(WordExportNotFoundError):
        generate_docx(
            program_id=data['program'].id,
            discipline_id=data['discipline'].id,
            filters={},
        )


def test_clone_from_trash_maps_competence_by_code_and_type_to_active_program(trash_schema):
    old = _program_bundle(prompt='Задание из корзины')
    ProgramTrashService().move_to_trash(old['program'], user=old['teacher_user'])

    active_program = EducationalProgram.objects.create(
        program_profile=old['profile'],
        department=old['department'],
        admission_year=old['program'].admission_year,
    )
    target_program_discipline = ProgramDiscipline.objects.create(
        educational_program=active_program,
        discipline=old['discipline'],
    )
    target_competence = Competence.objects.create(
        educational_program=active_program,
        competence_type=old['competence_type'],
        code=old['competence'].code,
        name='Новая формулировка',
    )
    DisciplineCompetence.objects.create(
        program_discipline=target_program_discipline,
        competence=target_competence,
    )

    new_item, transferred = clone_assessment_item_to_program_discipline(
        old['item'],
        target_program_discipline,
    )

    assert new_item.program_discipline == target_program_discipline
    assert new_item.competence == target_competence
    assert transferred == [target_competence]
    assert list(new_item.rows.values_list('left_text', flat=True)) == ['A']


def test_clone_to_trash_program_is_blocked(trash_schema):
    data = _program_bundle()
    ProgramTrashService().move_to_trash(data['program'], user=data['teacher_user'])

    with pytest.raises(ValueError):
        clone_assessment_item_to_program_discipline(data['item'], data['program_discipline'])


def test_hard_delete_removes_program_owned_data_only(trash_schema):
    data = _program_bundle()
    ProgramTrashService().move_to_trash(data['program'], user=data['teacher_user'])

    ProgramTrashService().hard_delete(data['program'])

    assert not EducationalProgram.objects.filter(pk=data['program'].pk).exists()
    assert not ProgramDiscipline.objects.filter(pk=data['program_discipline'].pk).exists()
    assert not Competence.objects.filter(pk=data['competence'].pk).exists()
    assert not CompetenceIndicator.objects.filter(pk=data['indicator'].pk).exists()
    assert not CompetenceIndicatorImport.objects.filter(pk=data['indicator_import'].pk).exists()
    assert not AssessmentItem.objects.filter(pk=data['item'].pk).exists()
    assert Discipline.objects.filter(pk=data['discipline'].pk).exists()
    assert Department.objects.filter(pk=data['department'].pk).exists()
    assert Teacher.objects.filter(user=data['teacher_user']).exists()


def test_restore_conflict_is_blocked(trash_schema):
    data = _program_bundle()
    ProgramTrashService().move_to_trash(data['program'], user=data['teacher_user'])
    EducationalProgram.objects.create(
        program_profile=data['profile'],
        department=data['department'],
        admission_year=data['program'].admission_year,
    )

    with pytest.raises(ProgramTrashConflictError):
        ProgramTrashService().restore_from_trash(data['program'], user=data['teacher_user'])


def test_restore_without_conflict_works(trash_schema):
    data = _program_bundle()
    ProgramTrashService().move_to_trash(data['program'], user=data['teacher_user'])

    ProgramTrashService().restore_from_trash(data['program'], user=data['teacher_user'])

    data['program'].refresh_from_db()
    assert data['program'].is_deleted is False
    assert data['program'].deleted_at is None


@override_settings(ALLOWED_HOSTS=['testserver'])
def test_restore_view_confirms_and_returns_program_to_active_workspace(trash_schema):
    data = _program_bundle()
    ProgramTrashService().move_to_trash(data['program'], user=data['teacher_user'])
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='secret',
    )
    client = Client()
    client.force_login(admin)
    restore_url = reverse('programs_trash_restore', args=[data['program'].pk])

    response = client.get(restore_url)

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Восстановить программу' in content
    assert 'Дисциплин учебного плана' in content
    assert str(ProgramTrashService().get_counts(data['program']).assessment_items) in content

    response = client.post(restore_url)

    data['program'].refresh_from_db()
    assert response.status_code == 302
    assert data['program'].is_deleted is False
    assert response['Location'].endswith(
        reverse('programs_educational_program_detail', args=[data['program'].pk])
    )
