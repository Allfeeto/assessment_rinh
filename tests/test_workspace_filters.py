import json

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.db import connection
from django.http import HttpResponse
from django.test import Client, override_settings
from django.urls import path, reverse

from assessment.views import TeacherWorkspaceView, TrashTeacherWorkspaceView
from assessment.models import AssessmentItem, AssessmentItemCompetence, AssessmentItemRow
from competencies.models import Competence, DisciplineCompetence
from core.models import AcademicDegree, AcademicTitle, AssessmentItemType, CompetenceType, EducationLevel
from core.permissions import SENIOR_TEACHER_GROUP_NAME
from core.views import lookup_options
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from teachers.models import Department, Teacher, TeacherProgramDiscipline


def _dummy_view(request, *args, **kwargs):
    return HttpResponse('ok')


urlpatterns = [
    path('login/', _dummy_view, name='login'),
    path('logout/', _dummy_view, name='logout'),
    path('assessment/workspace/', TeacherWorkspaceView.as_view(), name='assessment_workspace'),
    path('assessment/workspace/copy/', _dummy_view, name='assessment_workspace_copy'),
    path('assessment/workspace/paste/', _dummy_view, name='assessment_workspace_paste'),
    path(
        'assessment/workspace/clipboard/clear/',
        _dummy_view,
        name='assessment_workspace_clipboard_clear',
    ),
    path('assessment/trash-workspace/', TrashTeacherWorkspaceView.as_view(), name='assessment_trash_workspace'),
    path('assessment/trash-workspace/copy/', _dummy_view, name='assessment_trash_workspace_copy'),
    path('assessment/trash-items/<int:pk>/', _dummy_view, name='assessment_trash_detail'),
    path('assessment/create/', _dummy_view, name='assessment_create'),
    path('assessment/<int:pk>/', _dummy_view, name='assessment_detail'),
    path('assessment/<int:pk>/edit/', _dummy_view, name='assessment_update'),
    path('assessment/<int:pk>/delete/', _dummy_view, name='assessment_delete'),
    path('core/lookup/', lookup_options, name='core_lookup'),
]

WORKSPACE_TEST_SETTINGS = {
    'ALLOWED_HOSTS': ['testserver'],
    'ROOT_URLCONF': __name__,
}


@pytest.fixture()
def workspace_schema():
    if connection.vendor != 'sqlite':
        pytest.skip('Тесты фильтров рабочей области создают временную схему только в sqlite.')

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


def _create_program_bundle(
    *,
    index,
    year,
    program_department,
    item_type,
    competence_type,
    teacher=None,
    discipline_department=None,
    is_deleted=False,
):
    level = EducationLevel.objects.create(name=f'Уровень {index}')
    direction = TrainingDirection.objects.create(
        education_level=level,
        code=f'90.03.{index:02d}',
        name=f'Направление {index}',
    )
    profile = ProgramProfile.objects.create(
        training_direction=direction,
        code=f'90.03.{index:02d}.01',
        name=f'Профиль {index}',
    )
    program = EducationalProgram.objects.create(
        program_profile=profile,
        department=program_department,
        admission_year=year,
        is_deleted=is_deleted,
    )
    discipline = Discipline.objects.create(name=f'Дисциплина {index}')
    program_discipline = ProgramDiscipline.objects.create(
        educational_program=program,
        discipline=discipline,
        discipline_code=f'Б1.О.{index:02d}',
        department=discipline_department or program_department,
    )
    competence = Competence.objects.create(
        educational_program=program,
        competence_type=competence_type,
        code=f'ПК-{index}',
        name=f'Компетенция {index}',
    )
    DisciplineCompetence.objects.create(
        program_discipline=program_discipline,
        competence=competence,
    )
    item = AssessmentItem.objects.create(
        program_discipline=program_discipline,
        competence=competence,
        assessment_item_type=item_type,
        prompt_text=f'Задание {index}',
    )
    AssessmentItemCompetence.objects.create(assessment_item=item, competence=competence)
    AssessmentItemRow.objects.create(
        assessment_item=item,
        left_text='A',
        sort_order=1,
        is_correct=True,
    )
    if teacher is not None:
        TeacherProgramDiscipline.objects.create(
            teacher=teacher,
            program_discipline=program_discipline,
        )
    return program, program_discipline, item


def _base_workspace_refs():
    item_type = AssessmentItemType.objects.create(code='single', name='Один ответ')
    competence_type = CompetenceType.objects.create(name='ПК')
    department_a = Department.objects.create(
        number='10',
        short_name='ИБ',
        full_name='Информационная безопасность',
    )
    department_b = Department.objects.create(
        number='22',
        short_name='ИСиПИ',
        full_name='Информационные системы',
    )
    user = User.objects.create_user(username='workspace-teacher')
    teacher = Teacher.objects.create(
        user=user,
        department=department_a,
        full_name='Преподаватель рабочей области',
    )
    teacher.departments.add(department_a)
    return item_type, competence_type, department_a, department_b, user, teacher


def _response_context(response):
    return response.context or response.context_data


@override_settings(**WORKSPACE_TEST_SETTINGS)
def test_workspace_filters_by_year_and_program_department(workspace_schema):
    item_type, competence_type, department_a, department_b, user, teacher = _base_workspace_refs()
    old_program, _old_pd, _old_item = _create_program_bundle(
        index=1,
        year=2025,
        program_department=department_a,
        item_type=item_type,
        competence_type=competence_type,
        teacher=teacher,
    )
    new_program, new_pd, _new_item = _create_program_bundle(
        index=2,
        year=2026,
        program_department=department_b,
        item_type=item_type,
        competence_type=competence_type,
        teacher=teacher,
    )
    client = Client()
    client.force_login(user)

    response = client.get(
        reverse('assessment_workspace'),
        {
            'year': '2026',
            'department': str(department_b.id),
            'program': str(old_program.id),
        },
    )

    assert response.status_code == 200
    context = _response_context(response)
    assert context['selected_year'] == '2026'
    assert context['selected_department'] == str(department_b.id)
    assert context['selected_program'] == str(new_program.id)
    assert [program.id for program in context['programs']] == [new_program.id]
    assert [pd.id for pd in context['available_program_disciplines']] == [new_pd.id]
    content = response.content.decode()
    assert 'Задание 2' in content
    assert 'Задание 1' not in content
    assert 'data-autocomplete-parent="id_program"' in content
    assert 'data-autocomplete-parent-required="1"' in content
    assert 'Можно искать по коду' not in content
    assert f'>{new_program.full_display_name}</option>' in content
    assert f'>{new_pd.discipline_display_name}</option>' in content


@override_settings(**WORKSPACE_TEST_SETTINGS)
def test_workspace_invalid_filter_ids_do_not_raise_500(workspace_schema):
    item_type, competence_type, department_a, _department_b, user, teacher = _base_workspace_refs()
    _create_program_bundle(
        index=1,
        year=2026,
        program_department=department_a,
        item_type=item_type,
        competence_type=competence_type,
        teacher=teacher,
    )
    client = Client()
    client.force_login(user)

    response = client.get(
        reverse('assessment_workspace'),
        {
            'year': 'wrong',
            'department': '999999',
            'program': '999999',
            'program_discipline': 'bad',
        },
    )

    assert response.status_code == 200
    context = _response_context(response)
    assert context['selected_year'] == ''
    assert context['selected_department'] == ''


@override_settings(**WORKSPACE_TEST_SETTINGS)
def test_educational_program_autocomplete_filters_by_year_department_and_access(workspace_schema):
    item_type, competence_type, department_a, department_b, user, teacher = _base_workspace_refs()
    allowed_program, _allowed_pd, _allowed_item = _create_program_bundle(
        index=1,
        year=2026,
        program_department=department_b,
        item_type=item_type,
        competence_type=competence_type,
        teacher=teacher,
    )
    forbidden_program, _forbidden_pd, _forbidden_item = _create_program_bundle(
        index=2,
        year=2026,
        program_department=department_b,
        item_type=item_type,
        competence_type=competence_type,
        teacher=None,
    )
    _create_program_bundle(
        index=3,
        year=2025,
        program_department=department_a,
        item_type=item_type,
        competence_type=competence_type,
        teacher=teacher,
    )
    client = Client()
    client.force_login(user)

    response = client.get(
        reverse('core_lookup'),
        {
            'kind': 'educational_program',
            'year': '2026',
            'department_id': str(department_b.id),
            'q': '90.03',
        },
    )

    assert response.status_code == 200
    results = json.loads(response.content)['results']
    assert [result['id'] for result in results] == [allowed_program.id]
    assert '90.03.01.01 — Профиль 1, набор 2026, ИСиПИ, Уровень 1' == results[0]['label']

    response = client.get(
        reverse('core_lookup'),
        {
            'kind': 'educational_program',
            'selected_id': str(forbidden_program.id),
        },
    )

    assert json.loads(response.content)['results'] == []


@override_settings(**WORKSPACE_TEST_SETTINGS)
def test_program_discipline_autocomplete_uses_short_label_when_program_selected(workspace_schema):
    item_type, competence_type, department_a, _department_b, user, teacher = _base_workspace_refs()
    program, program_discipline, _item = _create_program_bundle(
        index=7,
        year=2026,
        program_department=department_a,
        item_type=item_type,
        competence_type=competence_type,
        teacher=teacher,
    )
    client = Client()
    client.force_login(user)

    response = client.get(
        reverse('core_lookup'),
        {
            'kind': 'program_discipline',
            'educational_program_id': str(program.id),
            'q': 'Б1.О.07',
        },
    )

    assert response.status_code == 200
    results = json.loads(response.content)['results']
    assert results == [
        {
            'id': program_discipline.id,
            'label': 'Б1.О.07 — Дисциплина 7',
        }
    ]


@override_settings(**WORKSPACE_TEST_SETTINGS)
def test_trash_workspace_and_autocomplete_use_deleted_programs_only(workspace_schema):
    item_type, competence_type, department_a, department_b, user, teacher = _base_workspace_refs()
    active_program, _active_pd, _active_item = _create_program_bundle(
        index=1,
        year=2026,
        program_department=department_a,
        item_type=item_type,
        competence_type=competence_type,
        teacher=teacher,
        is_deleted=False,
    )
    deleted_program, deleted_pd, _deleted_item = _create_program_bundle(
        index=2,
        year=2026,
        program_department=department_b,
        item_type=item_type,
        competence_type=competence_type,
        teacher=teacher,
        is_deleted=True,
    )
    client = Client()
    client.force_login(user)

    response = client.get(
        reverse('assessment_trash_workspace'),
        {
            'year': '2026',
            'department': str(department_b.id),
            'program': str(active_program.id),
        },
    )

    assert response.status_code == 200
    context = _response_context(response)
    assert context['selected_program'] == str(deleted_program.id)
    assert [program.id for program in context['programs']] == [deleted_program.id]
    assert [pd.id for pd in context['available_program_disciplines']] == [deleted_pd.id]
    assert 'Задание 2' in response.content.decode()

    response = client.get(
        reverse('core_lookup'),
        {
            'kind': 'educational_program',
            'deleted_only': '1',
            'year': '2026',
            'department_id': str(department_b.id),
            'q': '90.03',
        },
    )
    results = json.loads(response.content)['results']

    assert [result['id'] for result in results] == [deleted_program.id]
    assert active_program.id not in {result['id'] for result in results}


@override_settings(**WORKSPACE_TEST_SETTINGS)
def test_senior_teacher_scope_uses_discipline_department_not_program_department(workspace_schema):
    item_type = AssessmentItemType.objects.create(code='single', name='Один ответ')
    competence_type = CompetenceType.objects.create(name='ПК')
    managed_department = Department.objects.create(
        number='22',
        short_name='ИСиПИ',
        full_name='Информационные системы',
    )
    program_department = Department.objects.create(
        number='10',
        short_name='ИБ',
        full_name='Информационная безопасность',
    )
    senior_group = Group.objects.create(name=SENIOR_TEACHER_GROUP_NAME)
    senior_user = User.objects.create_user(username='senior')
    senior_user.groups.add(senior_group)
    senior_teacher = Teacher.objects.create(
        user=senior_user,
        department=managed_department,
        full_name='Старший преподаватель',
    )
    senior_teacher.departments.add(managed_department)
    program, _pd, _item = _create_program_bundle(
        index=1,
        year=2026,
        program_department=program_department,
        discipline_department=managed_department,
        item_type=item_type,
        competence_type=competence_type,
    )
    client = Client()
    client.force_login(senior_user)

    response = client.get(
        reverse('core_lookup'),
        {
            'kind': 'educational_program',
            'department_id': str(program_department.id),
            'q': '90.03',
        },
    )
    assert [result['id'] for result in json.loads(response.content)['results']] == [program.id]

    response = client.get(
        reverse('core_lookup'),
        {
            'kind': 'educational_program',
            'department_id': str(managed_department.id),
            'q': '90.03',
        },
    )
    assert json.loads(response.content)['results'] == []
