import random
from types import SimpleNamespace

import pytest

from assessment import services as assessment_services
from assessment import views as assessment_views
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
