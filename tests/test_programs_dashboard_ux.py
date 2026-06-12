from datetime import timedelta

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from competencies.forms import CompetenceIndicatorImportForm
from competencies.models import CompetenceIndicatorImport
from core.models import AcademicDegree, AcademicTitle, EducationLevel
from programs.models import (
    EducationalProgram,
    ProgramPlxImportDraft,
    ProgramProfile,
    TrainingDirection,
)
from programs.services.plx_dto import (
    DepartmentInfoDTO,
    PlxProgramImportDTO,
    ProgramInfoDTO,
)
from teachers.models import Department, Teacher


PROGRAMS_UX_SETTINGS = {
    'ALLOWED_HOSTS': ['testserver'],
}


def _response_context(response):
    return response.context or response.context_data


@pytest.fixture()
def programs_ux_schema():
    if connection.vendor != 'sqlite':
        pytest.skip('UX-тесты страницы программ создают временную схему только в sqlite.')

    models = [
        ContentType,
        Permission,
        Group,
        User,
        Session,
        EducationLevel,
        AcademicDegree,
        AcademicTitle,
        Department,
        Teacher,
        TrainingDirection,
        ProgramProfile,
        EducationalProgram,
        ProgramPlxImportDraft,
        CompetenceIndicatorImport,
    ]
    with connection.schema_editor() as schema_editor:
        for model in models:
            schema_editor.create_model(model)
    yield
    with connection.schema_editor() as schema_editor:
        for model in reversed(models):
            schema_editor.delete_model(model)


def _create_dashboard_data(count=25, import_count=25):
    user = User.objects.create_superuser(username='programs-admin')
    level = EducationLevel.objects.create(name='бакалавриат')
    department = Department.objects.create(
        number='22',
        short_name='ИС',
        full_name='Кафедра информационных систем',
    )
    programs = []
    for index in range(1, count + 1):
        direction = TrainingDirection.objects.create(
            education_level=level,
            code=f'90.03.{index:02d}',
            name=f'Направление {index:02d}',
        )
        profile = ProgramProfile.objects.create(
            training_direction=direction,
            code=f'90.03.{index:02d}.01',
            name=f'Профиль {index:02d}',
        )
        programs.append(
            EducationalProgram.objects.create(
                program_profile=profile,
                department=department,
                admission_year=2026,
            )
        )
    for index in range(1, import_count + 1):
        CompetenceIndicatorImport.objects.create(
            educational_program=programs[(index - 1) % len(programs)],
            uploaded_by=user,
            source_filename=f'indicators-{index:02d}.doc',
            source_sha256=f'{index:064x}',
            status=CompetenceIndicatorImport.Status.COMPLETED,
            total_rows=index,
            created_count=index,
        )
    return user, programs


def _draft_payload():
    return PlxProgramImportDTO(
        source_filename='active-preview.plx',
        program=ProgramInfoDTO(
            education_level_name='бакалавриат',
            training_direction_code='90.03.01',
            training_direction_name='Направление 01',
            profile_code='90.03.01.01',
            profile_name='Профиль 01',
            admission_year=2026,
        ),
        department=DepartmentInfoDTO(
            number='22',
            short_name='ИС',
            full_name='Кафедра информационных систем',
        ),
    ).to_dict()


@override_settings(**PROGRAMS_UX_SETTINGS)
def test_programs_dashboard_uses_compact_server_previews_and_autocomplete(programs_ux_schema):
    user, _programs = _create_dashboard_data()
    client = Client()
    client.force_login(user)

    with CaptureQueriesContext(connection) as queries:
        response = client.get(reverse('programs_root'))

    assert response.status_code == 200
    context = _response_context(response)
    assert len(context['directions_block']['items']) == 8
    assert len(context['profiles_block']['items']) == 8
    assert len(context['programs_block']['items']) == 8
    assert len(context['indicator_imports_block']['items']) == 3
    assert context['directions_block']['can_expand'] is True
    assert context['indicator_imports_block']['can_expand'] is True
    assert len(queries) <= 20

    content = response.content.decode()
    assert 'data-autocomplete-kind="educational_program"' in content
    assert 'purpose=indicator_import' in content
    assert '<option value="1">' not in content
    assert 'Корзина программ' in content
    assert 'Строк на странице' not in content


@override_settings(**PROGRAMS_UX_SETTINGS)
def test_programs_dashboard_blocks_expand_and_paginate_independently(programs_ux_schema):
    user, _programs = _create_dashboard_data()
    client = Client()
    client.force_login(user)

    response = client.get(
        reverse('programs_root'),
        {
            'directions_expanded': '1',
            'directions_page': '2',
            'profiles_expanded': '1',
            'profiles_page': '2',
            'programs_expanded': '1',
            'programs_page': '2',
            'programs_per_page': '20',
            'indicator_imports_expanded': '1',
            'indicator_imports_page': '2',
        },
    )

    assert response.status_code == 200
    context = _response_context(response)
    for key in ('directions_block', 'profiles_block', 'programs_block', 'indicator_imports_block'):
        assert context[key]['expanded'] is True
        assert context[key]['page_obj'].number == 2
        assert len(context[key]['items']) == 5
    assert context['programs_per_page'] == 20

    content = response.content.decode()
    assert 'profiles_expanded=1' in content
    assert 'programs_expanded=1' in content
    assert 'indicator_imports_expanded=1' in content
    assert 'Показывать программ на странице' in content


@override_settings(**PROGRAMS_UX_SETTINGS)
def test_programs_dashboard_returns_only_requested_compact_block(programs_ux_schema):
    user, _programs = _create_dashboard_data()
    client = Client()
    client.force_login(user)

    response = client.get(
        reverse('programs_root'),
        {'directions_expanded': '1', '_fragment': 'directions'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest',
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Направление 20' in content
    assert 'Свернуть список' in content
    assert '<h1 class="page-title">' not in content
    assert 'Образовательные программы' not in content


@override_settings(**PROGRAMS_UX_SETTINGS)
def test_active_plx_mode_hides_unrelated_blocks_and_session_contains_only_draft_id(programs_ux_schema):
    user, programs = _create_dashboard_data(count=1, import_count=1)
    draft = ProgramPlxImportDraft.objects.create(
        uploaded_by=user,
        existing_program=programs[0],
        source_filename='active-preview.plx',
        dto_payload=_draft_payload(),
        expires_at=timezone.now() + timedelta(hours=1),
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session['plx_import_draft_id'] = draft.id
    session.save()

    response = client.get(reverse('programs_root'))

    assert response.status_code == 200
    context = _response_context(response)
    assert context['plx_import_active'] is True
    assert 'directions_block' not in context
    assert client.session['plx_import_draft_id'] == draft.id
    assert isinstance(client.session['plx_import_draft_id'], int)
    content = response.content.decode()
    assert '<h1 class="page-title">Импорт учебного плана PLX</h1>' in content
    assert 'Импорт индикаторов достижения компетенций из Word' not in content
    assert '<h2>Направления</h2>' not in content
    assert 'Корзина программ' not in content


def test_indicator_import_form_requires_autocomplete_selection(programs_ux_schema):
    user, programs = _create_dashboard_data(count=2, import_count=0)

    empty_form = CompetenceIndicatorImportForm(
        data={'educational_program': ''},
        files={'word_file': SimpleUploadedFile('indicators.doc', b'word')},
        request_user=user,
    )
    invalid_form = CompetenceIndicatorImportForm(
        data={'educational_program': '999999'},
        files={'word_file': SimpleUploadedFile('indicators.doc', b'word')},
        request_user=user,
    )
    selected_form = CompetenceIndicatorImportForm(
        data={'educational_program': str(programs[0].id)},
        files={'word_file': SimpleUploadedFile('indicators.doc', b'word')},
        request_user=user,
    )

    assert empty_form.is_valid() is False
    assert empty_form.errors['educational_program'] == [
        'Выберите образовательную программу из списка подсказок.'
    ]
    assert invalid_form.is_valid() is False
    assert invalid_form.errors['educational_program'] == [
        'Выберите образовательную программу из списка подсказок.'
    ]
    assert selected_form.is_valid() is True
    assert selected_form.cleaned_data['educational_program'] == programs[0]
    assert selected_form.fields['educational_program'].widget.attrs['data-autocomplete-kind'] == (
        'educational_program'
    )
