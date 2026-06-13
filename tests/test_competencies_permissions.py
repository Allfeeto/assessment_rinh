from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.http import Http404
from django.template.loader import render_to_string
from django.test import RequestFactory

from competencies.forms import CompetenceForm, DisciplineCompetenceForm
from competencies.models import Competence, DisciplineCompetence
from competencies.views import (
    CompetenceDetailView,
    CompetenceListView,
    CompetenceUpdateView,
    DisciplineCompetenceListView,
    DisciplineCompetenceUpdateView,
    _build_indicator_slots,
)
from core.models import AcademicDegree, AcademicTitle, CompetenceType, EducationLevel
from core.permissions import (
    SENIOR_TEACHER_GROUP_NAME,
    can_manage_competence,
    can_manage_program_discipline,
)
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from teachers.models import Department, Teacher


@pytest.fixture()
def competencies_permissions_schema():
    if connection.vendor != 'sqlite':
        pytest.skip('Тесты кафедральных прав используют временную sqlite-схему.')

    models = [
        ContentType,
        Permission,
        Group,
        User,
        EducationLevel,
        CompetenceType,
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
    ]
    with connection.schema_editor() as schema_editor:
        for model in models:
            schema_editor.create_model(model)

    yield

    with connection.schema_editor() as schema_editor:
        for model in reversed(models):
            schema_editor.delete_model(model)


def _context():
    senior_group = Group.objects.create(name=SENIOR_TEACHER_GROUP_NAME)
    senior_a = User.objects.create_user(username='senior-a')
    senior_b = User.objects.create_user(username='senior-b')
    senior_a.groups.add(senior_group)
    senior_b.groups.add(senior_group)

    department_a = Department.objects.create(number='10', short_name='A', full_name='Кафедра A')
    department_b = Department.objects.create(number='20', short_name='B', full_name='Кафедра B')
    teacher_a = Teacher.objects.create(user=senior_a, department=department_a, full_name='Старший A')
    teacher_b = Teacher.objects.create(user=senior_b, department=department_b, full_name='Старший B')
    teacher_a.departments.add(department_a)
    teacher_b.departments.add(department_b)

    level = EducationLevel.objects.create(name='Бакалавриат')
    direction = TrainingDirection.objects.create(
        education_level=level,
        code='09.03.01',
        name='Направление',
    )
    profile = ProgramProfile.objects.create(
        training_direction=direction,
        code='09.03.01.01',
        name='Профиль',
    )
    program_a = EducationalProgram.objects.create(
        program_profile=profile,
        department=department_a,
        admission_year=2026,
    )
    program_b = EducationalProgram.objects.create(
        program_profile=profile,
        department=department_b,
        admission_year=2026,
    )
    discipline_a = Discipline.objects.create(name='Дисциплина A')
    discipline_b = Discipline.objects.create(name='Дисциплина B')
    pd_a = ProgramDiscipline.objects.create(
        educational_program=program_a,
        discipline=discipline_a,
        discipline_code='Б1.О.01',
        department=department_a,
    )
    pd_b = ProgramDiscipline.objects.create(
        educational_program=program_a,
        discipline=discipline_b,
        discipline_code='Б1.О.02',
        department=department_b,
    )
    competence_type = CompetenceType.objects.create(name='ПК')
    competence_a = Competence.objects.create(
        educational_program=program_a,
        competence_type=competence_type,
        code='ПК-1',
        name='Компетенция программы A',
    )
    competence_b = Competence.objects.create(
        educational_program=program_b,
        competence_type=competence_type,
        code='ПК-2',
        name='Компетенция программы B',
    )
    link_a = DisciplineCompetence.objects.create(program_discipline=pd_a, competence=competence_a)
    link_b = DisciplineCompetence.objects.create(program_discipline=pd_b, competence=competence_a)
    return SimpleNamespace(
        senior_a=senior_a,
        senior_b=senior_b,
        department_a=department_a,
        department_b=department_b,
        program_a=program_a,
        program_b=program_b,
        competence_type=competence_type,
        competence_a=competence_a,
        competence_b=competence_b,
        pd_a=pd_a,
        pd_b=pd_b,
        link_a=link_a,
        link_b=link_b,
    )


def _request(user, path='/'):
    request = RequestFactory().get(path)
    request.user = user
    return request


def test_competence_and_matrix_use_their_respective_departments(competencies_permissions_schema):
    ctx = _context()

    assert can_manage_competence(ctx.senior_a, ctx.competence_a)
    assert not can_manage_competence(ctx.senior_b, ctx.competence_a)
    assert can_manage_program_discipline(ctx.senior_b, ctx.pd_b)

    competence_view = CompetenceListView()
    competence_view.setup(_request(ctx.senior_b, '/competencies/list/'))
    assert list(competence_view.get_queryset()) == [ctx.competence_b]

    matrix_view = DisciplineCompetenceListView()
    matrix_view.setup(_request(ctx.senior_b, '/competencies/discipline-competence/'))
    assert list(matrix_view.get_queryset()) == [ctx.link_b]


def test_competence_detail_actions_and_direct_update_match_department(
    competencies_permissions_schema,
):
    ctx = _context()

    own_response = CompetenceDetailView.as_view()(
        _request(ctx.senior_a, f'/competencies/list/{ctx.competence_a.id}/'),
        pk=ctx.competence_a.id,
    )
    own_response.render()
    own_html = own_response.content.decode()
    assert 'Редактировать' in own_html
    assert 'Удалить' in own_html

    own_update = CompetenceUpdateView.as_view()(
        _request(ctx.senior_a, f'/competencies/list/{ctx.competence_a.id}/edit/'),
        pk=ctx.competence_a.id,
    )
    assert own_update.status_code == 200

    with pytest.raises(Http404):
        CompetenceDetailView.as_view()(
            _request(ctx.senior_b, f'/competencies/list/{ctx.competence_a.id}/'),
            pk=ctx.competence_a.id,
        )
    with pytest.raises(Http404):
        CompetenceUpdateView.as_view()(
            _request(ctx.senior_b, f'/competencies/list/{ctx.competence_a.id}/edit/'),
            pk=ctx.competence_a.id,
        )


def test_forms_reject_foreign_competence_program_and_foreign_discipline(
    competencies_permissions_schema,
):
    ctx = _context()

    competence_form = CompetenceForm(
        data={
            'educational_program': ctx.program_b.id,
            'competence_type': ctx.competence_type.id,
            'code': 'ПК-3',
            'name': 'Чужая компетенция',
        },
        request_user=ctx.senior_a,
    )
    assert not competence_form.is_valid()
    assert 'educational_program' in competence_form.errors

    matrix_form = DisciplineCompetenceForm(
        data={
            'program_discipline': ctx.pd_b.id,
            'competence': ctx.competence_a.id,
        },
        request_user=ctx.senior_a,
    )
    assert not matrix_form.is_valid()
    assert 'program_discipline' in matrix_form.errors

    with pytest.raises(Http404):
        DisciplineCompetenceUpdateView.as_view()(
            _request(
                ctx.senior_a,
                f'/competencies/discipline-competence/{ctx.link_b.id}/edit/',
            ),
            pk=ctx.link_b.id,
        )


def test_indicator_slots_and_template_show_roles_and_missing_dash():
    indicators = [
        SimpleNamespace(code='ПК-1.1', text='Знает основы'),
        SimpleNamespace(code='ПК-1.3', text='Владеет методами'),
    ]
    slots = _build_indicator_slots(indicators)

    assert [slot['label'] for slot in slots] == ['Знать', 'Уметь', 'Владеть']
    assert slots[0]['indicator'].code == 'ПК-1.1'
    assert slots[1]['indicator'] is None
    assert slots[2]['indicator'].code == 'ПК-1.3'

    competence = SimpleNamespace(
        id=1,
        code='ПК-1',
        name='Компетенция',
        competence_type=SimpleNamespace(name='ПК'),
        educational_program='Программа',
        disciplines_count=1,
        indicator_slots=slots,
        items_count=0,
        can_manage=False,
    )
    html = render_to_string(
        'competencies/includes/competences_table.html',
        {
            'competences_block': {
                'items': [competence],
                'total_count': 1,
                'expanded': False,
                'can_expand': False,
            },
            'can_manage_competence_directory': False,
        },
    )
    assert 'Знать:' in html
    assert 'Уметь:' in html
    assert 'Владеть:' in html
    assert 'ПК-1.1' in html
    assert '—' in html
