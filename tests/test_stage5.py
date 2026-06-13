import random
from types import SimpleNamespace

import pytest
from django.test import RequestFactory
from django.utils.http import content_disposition_header

from assessment import services as assessment_services
from assessment import views as assessment_views
from export import views as export_views
from export import services as export_services


class FakeSession(dict):
    modified = False


def test_infer_item_type_code_prefers_stable_code():
    item_type = SimpleNamespace(code=assessment_services.TYPE_MATCHING, name='выбор одного ответа')

    assert assessment_services.infer_item_type_code(item_type) == assessment_services.TYPE_MATCHING


def test_infer_item_type_code_supports_legacy_code_alias():
    item_type = SimpleNamespace(code='multiple_choice', name='old value')

    assert assessment_services.infer_item_type_code(item_type) == assessment_services.TYPE_MULTIPLE


def test_clipboard_ids_are_sanitized_and_deduplicated():
    session = FakeSession()

    assessment_services.set_clipboard_item_ids(session, ['7', 7, 'bad', 11, None, '11'])

    assert assessment_services.get_clipboard_item_ids(session) == [7, 11]
    assert session.modified is True


def test_restrict_queryset_denies_anonymous_user():
    class FakeQueryset:
        def none(self):
            return 'empty'

    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False, is_superuser=False))

    assert assessment_views._restrict_queryset_for_teacher_user(request, FakeQueryset()) == 'empty'


def test_restrict_queryset_filters_teacher_scope(monkeypatch):
    class FakeQueryset:
        def __init__(self):
            self.filter_kwargs = None

        def filter(self, **kwargs):
            self.filter_kwargs = kwargs
            return self

    user = SimpleNamespace(
        is_authenticated=True,
        is_superuser=False,
        teacher_profile=SimpleNamespace(id=1),
    )
    queryset = FakeQueryset()
    monkeypatch.setattr(
        assessment_views,
        '_allowed_program_discipline_ids_for_user',
        lambda received_user: [10, 20],
    )

    result = assessment_views._restrict_queryset_for_teacher_user(SimpleNamespace(user=user), queryset)

    assert result is queryset
    assert queryset.filter_kwargs == {'program_discipline_id__in': [10, 20]}


def test_generate_docx_enforces_item_limit(monkeypatch):
    class FakeProgramDisciplineManager:
        def select_related(self, *args):
            return self

        def filter(self, **kwargs):
            return self

        def first(self):
            return object()

    class TooLargeQueryset:
        def count(self):
            return export_services.MAX_EXPORT_ITEMS + 1

    monkeypatch.setattr(
        export_services,
        'ProgramDiscipline',
        SimpleNamespace(objects=FakeProgramDisciplineManager()),
    )
    monkeypatch.setattr(export_services, '_filtered_items', lambda *args, **kwargs: TooLargeQueryset())

    with pytest.raises(export_services.WordExportError) as exc_info:
        export_services.generate_docx(program_id=1, discipline_id=2, filters={})

    assert str(export_services.MAX_EXPORT_ITEMS) in str(exc_info.value)


def test_prepare_export_item_hides_unknown_type_details():
    class EmptyRows:
        def order_by(self, *args):
            return []

    item = SimpleNamespace(
        id=42,
        assessment_item_type_id=99,
        assessment_item_type=SimpleNamespace(code='custom_private_type', name='Secret Internal Name'),
        rows=EmptyRows(),
        prompt_text='Prompt',
    )

    with pytest.raises(export_services.WordExportError) as exc_info:
        export_services._prepare_export_item(item, number=1, rng=random.Random(1))

    message = str(exc_info.value)
    assert 'Secret Internal Name' not in message
    assert 'неподдерживаемым типом' in message


def _fake_competence(pk, code, name=None, indicators=()):
    return SimpleNamespace(
        id=pk,
        code=code,
        name=name or f'Компетенция {code}',
        indicators=list(indicators),
    )


def _fake_indicator(pk, code, text):
    return SimpleNamespace(id=pk, code=code, text=text)


def _fake_type(pk, code, name=None):
    return SimpleNamespace(id=pk, code=code, name=name or code)


def _fake_item(pk, competence, item_type):
    return SimpleNamespace(
        id=pk,
        prompt_text=f'Задание {pk}',
        competence=competence,
        competence_id=competence.id if competence else None,
        assessment_item_type=item_type,
        assessment_item_type_id=item_type.id,
        _prefetched_objects_cache={
            'competence_links': [SimpleNamespace(competence=competence)] if competence else [],
        },
    )


def test_build_export_filename_uses_program_profile_code_and_sanitizes_special_chars():
    program = SimpleNamespace(id=10, program_profile=SimpleNamespace(code='09.03.02.01'))
    discipline = SimpleNamespace(id=20, name='  Философия: "этика"/право?\n')

    filename = export_services.build_export_filename(program, discipline)

    assert filename == '09.03.02.01_Философия этика право.docx'
    assert content_disposition_header(True, filename).startswith('attachment;')


def test_build_export_filename_falls_back_when_program_code_is_missing():
    program = SimpleNamespace(id=10, program_profile=SimpleNamespace(code=''))
    discipline = SimpleNamespace(id=20, name='Философия')

    assert export_services.build_export_filename(program, discipline) == 'program_10_Философия.docx'


def test_word_export_response_uses_safe_content_disposition(monkeypatch):
    program = SimpleNamespace(id=10, program_profile=SimpleNamespace(code='09.03.02.01'))
    discipline = SimpleNamespace(id=20, name='Философия: "этика"/право?')

    class FakeForm:
        cleaned_data = {
            'educational_program': program,
            'discipline': discipline,
            'assessment_item_type': None,
            'competence': None,
        }

        def __init__(self, *args, **kwargs):
            pass

        def is_valid(self):
            return True

        def add_error(self, *args, **kwargs):
            raise AssertionError('Unexpected form error')

    class FakeProgramDisciplineQuery:
        def filter(self, **kwargs):
            return self

        def values_list(self, *args, **kwargs):
            return self

        def first(self):
            return 123

    monkeypatch.setattr(export_views, 'WordExportForm', FakeForm)
    monkeypatch.setattr(
        export_views,
        'ProgramDiscipline',
        SimpleNamespace(objects=FakeProgramDisciplineQuery()),
    )
    monkeypatch.setattr(export_views, 'can_access_program_discipline', lambda user, program_discipline_id: True)
    monkeypatch.setattr(export_views, 'generate_docx', lambda **kwargs: b'docx')

    request = RequestFactory().get('/export/word/', {'download': '1'})
    request.user = SimpleNamespace(id=1, is_authenticated=True)

    response = export_views.WordExportView().get(request)

    assert response.status_code == 200
    assert response.content == b'docx'
    header = response['Content-Disposition']
    assert header.startswith('attachment;')
    assert "filename*=utf-8''09.03.02.01_%D0%A4" in header
    assert '%22' not in header


def test_sort_assessment_items_groups_by_competence_type_and_id():
    comp_a = _fake_competence(1, 'ОПК-1')
    comp_b = _fake_competence(2, 'УК-2')
    type_single = _fake_type(1, assessment_services.TYPE_SINGLE)
    type_multiple = _fake_type(2, assessment_services.TYPE_MULTIPLE)
    items = [
        _fake_item(5, comp_b, type_single),
        _fake_item(4, comp_a, type_single),
        _fake_item(3, comp_a, type_multiple),
        _fake_item(2, comp_a, type_multiple),
    ]

    sorted_ids = [item.id for item in export_services.sort_assessment_items(items)]

    assert sorted_ids == [2, 3, 4, 5]


def test_build_numbered_items_assigns_numbers_after_sort(monkeypatch):
    comp_a = _fake_competence(1, 'ОПК-1')
    comp_b = _fake_competence(2, 'УК-2')
    item_type = _fake_type(1, assessment_services.TYPE_SINGLE)
    items = [
        _fake_item(1, comp_b, item_type),
        _fake_item(3, comp_a, item_type),
        _fake_item(2, comp_a, item_type),
    ]

    def fake_prepare(item, number, rng):
        return {'item_id': item.id, 'number': number}

    monkeypatch.setattr(export_services, '_prepare_export_item', fake_prepare)

    numbered = export_services.build_numbered_items(items, rng=random.Random(1))

    assert numbered == [
        {'item_id': 2, 'number': 1},
        {'item_id': 3, 'number': 2},
        {'item_id': 1, 'number': 3},
    ]


def test_prepare_export_item_adds_indicators_for_linked_competences():
    indicators = [
        _fake_indicator(3, 'ОПК-1.3', 'Владеет навыками анализа'),
        _fake_indicator(2, 'ОПК-1.2', 'Умеет применять знания'),
        _fake_indicator(1, 'ОПК-1.1', 'Знает основные положения'),
    ]
    competence = _fake_competence(1, 'ОПК-1', indicators=indicators)
    item_type = _fake_type(1, assessment_services.TYPE_OPEN)
    item = _fake_item(1, competence, item_type)
    item.rows = SimpleNamespace(order_by=lambda *args: [])

    prepared = export_services._prepare_export_item(item, number=1, rng=random.Random(1))

    assert prepared['indicator_text'] == (
        'ОПК-1.1 — Знает основные положения\n'
        'ОПК-1.2 — Умеет применять знания\n'
        'ОПК-1.3 — Владеет навыками анализа'
    )


def test_prepare_export_item_uses_dash_when_competence_has_no_indicators():
    competence = _fake_competence(1, 'ОПК-1')
    item_type = _fake_type(1, assessment_services.TYPE_OPEN)
    item = _fake_item(1, competence, item_type)
    item.rows = SimpleNamespace(order_by=lambda *args: [])

    prepared = export_services._prepare_export_item(item, number=1, rng=random.Random(1))

    assert prepared['indicator_text'] == '—'


def test_get_item_competences_merges_legacy_fk_with_m2m_links():
    comp_a = _fake_competence(1, 'ОПК-1')
    comp_b = _fake_competence(2, 'УК-2')
    item = SimpleNamespace(
        competence=comp_a,
        competence_id=comp_a.id,
        _prefetched_objects_cache={
            'competence_links': [SimpleNamespace(competence=comp_b)],
        },
    )

    assert [competence.id for competence in assessment_services.get_item_competences(item)] == [2, 1]


def test_build_specification_groups_merges_rows_by_competence_indicator_and_type():
    comp_a = 'ОПК-1 — Способен применять базовые знания'
    comp_b = 'УК-2 — Умеет тестировать БД'
    type_one = 'Задание закрытого типа с выбором одного ответа'
    type_open = 'Открытое задание'
    prepared_items = [
        {'number': 1, 'competence_text': comp_a, 'indicator_text': '—', 'type_name': type_one},
        {'number': 2, 'competence_text': comp_a, 'indicator_text': '—', 'type_name': type_one},
        {'number': 3, 'competence_text': comp_a, 'indicator_text': '—', 'type_name': type_open},
        {'number': 4, 'competence_text': comp_b, 'indicator_text': '—', 'type_name': type_one},
    ]

    groups = export_services.build_specification_groups(prepared_items)

    assert [
        (group['competence_text'], group['indicator_text'], group['numbers_text'], group['type_name'])
        for group in groups
    ] == [
        (comp_a, '—', '1, 2', type_one),
        (comp_a, '—', '3', type_open),
        (comp_b, '—', '4', type_one),
    ]
