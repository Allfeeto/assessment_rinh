from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.template.loader import render_to_string
from django.test import RequestFactory

from core.models import AcademicDegree, AcademicTitle, EducationLevel
from core.permissions import (
    DOMAIN_MANAGER_REQUIRED_PERMISSIONS,
    SENIOR_TEACHER_GROUP_NAME,
    can_assign_teacher_to_program_discipline,
    can_manage_program_discipline,
    is_superuser_or_platform_admin,
)
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from teachers.forms import TeacherForm
from teachers.models import Department, Teacher, TeacherProgramDiscipline
from teachers.views import TeacherAssignmentToggleView, _build_assignment_rows


@pytest.fixture()
def department_permissions_schema():
    if connection.vendor != 'sqlite':
        pytest.skip('Тесты кафедральных прав используют временную sqlite-схему.')

    models = [
        ContentType,
        Permission,
        Group,
        User,
        EducationLevel,
        AcademicDegree,
        AcademicTitle,
        Department,
        Teacher,
        TrainingDirection,
        ProgramProfile,
        EducationalProgram,
        Discipline,
        ProgramDiscipline,
        TeacherProgramDiscipline,
    ]

    with connection.schema_editor() as schema_editor:
        for model in models:
            schema_editor.create_model(model)

    yield

    with connection.schema_editor() as schema_editor:
        for model in reversed(models):
            schema_editor.delete_model(model)


def _grant_domain_manager_required_permissions(group):
    for permission_path in DOMAIN_MANAGER_REQUIRED_PERMISSIONS:
        app_label, codename = permission_path.split('.', 1)
        model_name = codename.split('_', 1)[1]
        content_type, _ = ContentType.objects.get_or_create(
            app_label=app_label,
            model=model_name,
        )
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={'name': codename},
        )
        group.permissions.add(permission)


def _create_context():
    senior_group = Group.objects.create(name=SENIOR_TEACHER_GROUP_NAME)
    _grant_domain_manager_required_permissions(senior_group)
    admin = User.objects.create_superuser(username='admin')
    senior_ib_user = User.objects.create_user(username='senior_ib')
    senior_isipi_user = User.objects.create_user(username='senior_isipi')
    senior_empty_user = User.objects.create_user(username='senior_empty')
    senior_ib_user.groups.add(senior_group)
    senior_isipi_user.groups.add(senior_group)
    senior_empty_user.groups.add(senior_group)

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
    ib = Department.objects.create(number='10', short_name='ИБ', full_name='Информационная безопасность')
    isipi = Department.objects.create(number='22', short_name='ИСиПИ', full_name='Информационные системы')
    program = EducationalProgram.objects.create(
        program_profile=profile,
        department=ib,
        admission_year=2026,
    )

    senior_ib_teacher = Teacher.objects.create(
        user=senior_ib_user,
        department=ib,
        full_name='Старший ИБ',
    )
    senior_ib_teacher.departments.add(ib)
    senior_isipi_teacher = Teacher.objects.create(
        user=senior_isipi_user,
        department=isipi,
        full_name='Старший ИСиПИ',
    )
    senior_isipi_teacher.departments.add(isipi)
    Teacher.objects.create(
        user=senior_empty_user,
        department=ib,
        full_name='Старший без кафедр',
    )

    teacher_ib = Teacher.objects.create(department=ib, full_name='Преподаватель ИБ')
    teacher_ib.departments.add(ib)
    teacher_isipi = Teacher.objects.create(department=isipi, full_name='Преподаватель ИСиПИ')
    teacher_isipi.departments.add(isipi)
    teacher_multi = Teacher.objects.create(department=ib, full_name='Преподаватель ИБ и ИСиПИ')
    teacher_multi.departments.add(ib, isipi)

    discipline_ib = Discipline.objects.create(name='Информационная безопасность')
    discipline_isipi = Discipline.objects.create(name='Разработка сайтов')
    discipline_without_department = Discipline.objects.create(name='Дисциплина без кафедры')
    pd_ib = ProgramDiscipline.objects.create(
        educational_program=program,
        discipline=discipline_ib,
        discipline_code='Б1.О.01',
        department=ib,
    )
    pd_isipi = ProgramDiscipline.objects.create(
        educational_program=program,
        discipline=discipline_isipi,
        discipline_code='Б1.О.02',
        department=isipi,
    )
    pd_without_department = ProgramDiscipline.objects.create(
        educational_program=program,
        discipline=discipline_without_department,
        discipline_code='Б1.О.03',
        department=None,
    )

    return SimpleNamespace(
        admin=admin,
        senior_ib_user=senior_ib_user,
        senior_isipi_user=senior_isipi_user,
        senior_empty_user=senior_empty_user,
        ib=ib,
        isipi=isipi,
        program=program,
        teacher_ib=teacher_ib,
        teacher_isipi=teacher_isipi,
        teacher_multi=teacher_multi,
        pd_ib=pd_ib,
        pd_isipi=pd_isipi,
        pd_without_department=pd_without_department,
    )


def test_assignment_permission_matrix_by_department(department_permissions_schema):
    ctx = _create_context()

    assert can_assign_teacher_to_program_discipline(ctx.admin, ctx.teacher_isipi, ctx.pd_ib)
    assert not is_superuser_or_platform_admin(ctx.senior_ib_user)
    assert can_assign_teacher_to_program_discipline(ctx.senior_ib_user, ctx.teacher_ib, ctx.pd_ib)
    assert not can_assign_teacher_to_program_discipline(ctx.senior_ib_user, ctx.teacher_isipi, ctx.pd_ib)
    assert not can_assign_teacher_to_program_discipline(ctx.senior_ib_user, ctx.teacher_ib, ctx.pd_isipi)
    assert can_assign_teacher_to_program_discipline(ctx.senior_ib_user, ctx.teacher_multi, ctx.pd_ib)
    assert not can_assign_teacher_to_program_discipline(ctx.senior_ib_user, ctx.teacher_multi, ctx.pd_isipi)
    assert can_assign_teacher_to_program_discipline(ctx.senior_isipi_user, ctx.teacher_multi, ctx.pd_isipi)
    assert not can_assign_teacher_to_program_discipline(ctx.senior_isipi_user, ctx.teacher_multi, ctx.pd_ib)
    assert not can_assign_teacher_to_program_discipline(
        ctx.senior_ib_user,
        ctx.teacher_ib,
        ctx.pd_without_department,
    )


def test_assignment_rows_keep_foreign_disciplines_visible_but_disabled(department_permissions_schema):
    ctx = _create_context()
    TeacherProgramDiscipline.objects.create(teacher=ctx.teacher_multi, program_discipline=ctx.pd_ib)
    TeacherProgramDiscipline.objects.create(teacher=ctx.teacher_multi, program_discipline=ctx.pd_isipi)

    rows = _build_assignment_rows(ctx.teacher_multi, ctx.program, '', ctx.senior_ib_user)
    rows_by_id = {row['id']: row for row in rows}

    assert rows_by_id[ctx.pd_ib.id]['can_assign'] is True
    assert rows_by_id[ctx.pd_isipi.id]['can_assign'] is False
    assert 'другой кафедре' in rows_by_id[ctx.pd_isipi.id]['cannot_assign_reason']
    assert rows_by_id[ctx.pd_without_department.id]['can_assign'] is False
    assert 'не указана кафедра' in rows_by_id[ctx.pd_without_department.id]['cannot_assign_reason']

    html = render_to_string(
        'teachers/_assignment_table.html',
        {
            'assignment_active_program': ctx.program,
            'assignment_rows': rows,
            'assignment_can_edit': True,
            'assignment_sort': 'code',
            'assignment_sort_dir': 'asc',
        },
    )
    assert f'data-program-discipline-id="{ctx.pd_ib.id}"' in html
    assert f'data-program-discipline-id="{ctx.pd_isipi.id}"' in html
    assert 'data-assignment-sort="code"' in html
    assert 'data-assignment-sort="discipline"' in html
    assert '<th>Дисциплина</th>' not in html
    assert 'Б1.О.01' in html
    assert 'Б1.О.01 — Информационная безопасность' not in html
    assert 'Нельзя назначить преподавателя: дисциплина относится к другой кафедре.' in html


def test_assignment_rows_sort_available_disciplines_first(department_permissions_schema):
    ctx = _create_context()
    unavailable_first_by_code = ProgramDiscipline.objects.create(
        educational_program=ctx.program,
        discipline=Discipline.objects.create(name='Анализ чужой кафедры'),
        discipline_code='Б1.О.00',
        department=ctx.isipi,
    )
    available_last_by_code = ProgramDiscipline.objects.create(
        educational_program=ctx.program,
        discipline=Discipline.objects.create(name='Языки программирования'),
        discipline_code='Б1.О.99',
        department=ctx.ib,
    )

    rows = _build_assignment_rows(ctx.teacher_multi, ctx.program, '', ctx.senior_ib_user)
    row_ids = [row['id'] for row in rows]
    unavailable_position = row_ids.index(unavailable_first_by_code.id)
    available_position = row_ids.index(available_last_by_code.id)

    assert available_position < unavailable_position
    assert [row['id'] for row in rows if row['can_assign']] == [
        ctx.pd_ib.id,
        available_last_by_code.id,
    ]


def test_assignment_rows_keep_assigned_disciplines_before_available(department_permissions_schema):
    ctx = _create_context()
    available_first_by_code = ProgramDiscipline.objects.create(
        educational_program=ctx.program,
        discipline=Discipline.objects.create(name='Алгоритмы своей кафедры'),
        discipline_code='Б1.О.00',
        department=ctx.ib,
    )
    assigned_foreign_last_by_code = ProgramDiscipline.objects.create(
        educational_program=ctx.program,
        discipline=Discipline.objects.create(name='Язык чужой кафедры'),
        discipline_code='Б1.О.99',
        department=ctx.isipi,
    )
    TeacherProgramDiscipline.objects.create(
        teacher=ctx.teacher_multi,
        program_discipline=assigned_foreign_last_by_code,
    )

    rows = _build_assignment_rows(ctx.teacher_multi, ctx.program, '', ctx.senior_ib_user)
    row_ids = [row['id'] for row in rows]

    assert row_ids.index(assigned_foreign_last_by_code.id) < row_ids.index(available_first_by_code.id)
    assert rows[0]['id'] == assigned_foreign_last_by_code.id
    assert rows[0]['is_assigned'] is True
    assert rows[0]['can_assign'] is False


def test_assignment_rows_sort_by_requested_column_inside_fixed_groups(department_permissions_schema):
    ctx = _create_context()
    available_first_by_name = ProgramDiscipline.objects.create(
        educational_program=ctx.program,
        discipline=Discipline.objects.create(name='Аналитические системы'),
        discipline_code='Б1.О.99',
        department=ctx.ib,
    )
    available_last_by_name = ProgramDiscipline.objects.create(
        educational_program=ctx.program,
        discipline=Discipline.objects.create(name='Языки программирования'),
        discipline_code='Б1.О.00',
        department=ctx.ib,
    )
    unavailable_first_by_name = ProgramDiscipline.objects.create(
        educational_program=ctx.program,
        discipline=Discipline.objects.create(name='Анализ чужой кафедры'),
        discipline_code='Б1.О.01',
        department=ctx.isipi,
    )
    assigned_foreign_last_by_name = ProgramDiscipline.objects.create(
        educational_program=ctx.program,
        discipline=Discipline.objects.create(name='Язык чужой кафедры'),
        discipline_code='Б1.О.98',
        department=ctx.isipi,
    )
    TeacherProgramDiscipline.objects.create(
        teacher=ctx.teacher_multi,
        program_discipline=assigned_foreign_last_by_name,
    )

    rows = _build_assignment_rows(
        ctx.teacher_multi,
        ctx.program,
        '',
        ctx.senior_ib_user,
        sort_by='discipline',
    )
    row_ids = [row['id'] for row in rows]
    available_ids = [row['id'] for row in rows if row['can_assign'] and not row['is_assigned']]
    unavailable_ids = [row['id'] for row in rows if not row['can_assign'] and not row['is_assigned']]

    assert row_ids[0] == assigned_foreign_last_by_name.id
    assert available_ids[:3] == [
        available_first_by_name.id,
        ctx.pd_ib.id,
        available_last_by_name.id,
    ]
    assert unavailable_ids[0] == unavailable_first_by_name.id

    descending_rows = _build_assignment_rows(
        ctx.teacher_multi,
        ctx.program,
        '',
        ctx.senior_ib_user,
        sort_by='discipline',
        sort_direction='desc',
    )
    descending_available_ids = [
        row['id']
        for row in descending_rows
        if row['can_assign'] and not row['is_assigned']
    ]
    assert descending_rows[0]['id'] == assigned_foreign_last_by_name.id
    assert descending_available_ids[:3] == [
        available_last_by_name.id,
        ctx.pd_ib.id,
        available_first_by_name.id,
    ]


def test_assignment_toggle_rejects_forbidden_direct_post(department_permissions_schema):
    ctx = _create_context()
    request = RequestFactory().post(
        '/teachers/assignments/toggle/',
        {
            'teacher_id': str(ctx.teacher_ib.id),
            'program_discipline_id': str(ctx.pd_isipi.id),
            'assign': '1',
        },
    )
    request.user = ctx.senior_ib_user

    response = TeacherAssignmentToggleView().post(request)

    assert response.status_code == 403
    assert not TeacherProgramDiscipline.objects.filter(
        teacher=ctx.teacher_ib,
        program_discipline=ctx.pd_isipi,
    ).exists()


def test_assignment_toggle_allows_department_match(department_permissions_schema):
    ctx = _create_context()
    request = RequestFactory().post(
        '/teachers/assignments/toggle/',
        {
            'teacher_id': str(ctx.teacher_ib.id),
            'program_discipline_id': str(ctx.pd_ib.id),
            'assign': '1',
        },
    )
    request.user = ctx.senior_ib_user

    response = TeacherAssignmentToggleView().post(request)

    assert response.status_code == 200
    assert TeacherProgramDiscipline.objects.filter(
        teacher=ctx.teacher_ib,
        program_discipline=ctx.pd_ib,
    ).exists()


def test_teacher_form_limits_create_to_senior_departments(department_permissions_schema):
    ctx = _create_context()

    foreign_form = TeacherForm(
        data={
            'department': ctx.isipi.id,
            'departments': [ctx.isipi.id],
            'full_name': 'Новый чужой преподаватель',
            'academic_degree': '',
            'academic_title': '',
        },
        request_user=ctx.senior_ib_user,
    )
    assert foreign_form.is_valid() is False

    own_form = TeacherForm(
        data={
            'department': ctx.ib.id,
            'departments': [ctx.ib.id],
            'full_name': 'Новый преподаватель ИБ',
            'academic_degree': '',
            'academic_title': '',
        },
        request_user=ctx.senior_ib_user,
    )
    assert own_form.is_valid(), own_form.errors
    teacher = own_form.save()
    assert set(teacher.departments.values_list('id', flat=True)) == {ctx.ib.id}


def test_teacher_form_preserves_foreign_department_links_for_senior(department_permissions_schema):
    ctx = _create_context()

    form = TeacherForm(
        data={
            'department': ctx.ib.id,
            'departments': [ctx.ib.id],
            'full_name': 'Обновленный преподаватель',
            'academic_degree': '',
            'academic_title': '',
        },
        instance=ctx.teacher_multi,
        request_user=ctx.senior_ib_user,
    )

    assert form.is_valid(), form.errors
    teacher = form.save()

    assert set(teacher.departments.values_list('id', flat=True)) == {ctx.ib.id, ctx.isipi.id}


def test_superuser_can_edit_all_teacher_departments(department_permissions_schema):
    ctx = _create_context()

    form = TeacherForm(
        data={
            'user': '',
            'department': ctx.isipi.id,
            'departments': [ctx.isipi.id],
            'full_name': 'Суперпользователь обновил кафедры',
            'academic_degree': '',
            'academic_title': '',
        },
        instance=ctx.teacher_multi,
        request_user=ctx.admin,
    )

    assert form.is_valid(), form.errors
    teacher = form.save()

    assert teacher.department_id == ctx.isipi.id
    assert set(teacher.departments.values_list('id', flat=True)) == {ctx.isipi.id}


def test_program_discipline_management_requires_senior_department(department_permissions_schema):
    ctx = _create_context()

    assert can_manage_program_discipline(ctx.senior_ib_user, ctx.pd_ib)
    assert not can_manage_program_discipline(ctx.senior_ib_user, ctx.pd_isipi)
    assert not can_manage_program_discipline(ctx.senior_ib_user, ctx.pd_without_department)
    assert can_manage_program_discipline(ctx.admin, ctx.pd_isipi)
