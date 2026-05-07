import json
from types import SimpleNamespace

from django.test import RequestFactory

from competencies import views as competency_views
from core.lookups import registered_lookup_kinds
from core.views import lookup_options


def _authenticated_user():
    return SimpleNamespace(is_authenticated=True)


def test_lookup_registry_contains_registered_app_kinds():
    assert set(registered_lookup_kinds()) >= {
        'assessment_item_type',
        'auth_user',
        'competence',
        'department',
        'discipline',
        'educational_program',
        'program_discipline',
        'program_profile',
        'teacher',
        'training_direction',
    }


def test_unknown_lookup_kind_keeps_empty_results_contract():
    request = RequestFactory().get('/core/lookup/', {'kind': 'missing'})
    request.user = _authenticated_user()

    response = lookup_options(request)

    assert response.status_code == 200
    assert json.loads(response.content) == {'results': []}


def test_legacy_competence_endpoint_delegates_to_generic_lookup(monkeypatch):
    captured = {}

    def fake_lookup(request, query, selected_id, limit):
        captured.update({'query': query, 'selected_id': selected_id, 'limit': limit})
        return [{'id': 1, 'label': 'УК-1 — Test'}]

    monkeypatch.setattr(competency_views, 'lookup_competence', fake_lookup)
    request = RequestFactory().get(
        '/competencies/by-program-discipline/',
        {'program_discipline_id': '10', 'linked_only': '1'},
    )
    request.user = _authenticated_user()

    response = competency_views.competences_by_program_discipline(request)

    assert response.status_code == 200
    assert captured == {'query': '', 'selected_id': None, 'limit': None}
    assert json.loads(response.content) == {'results': [{'id': 1, 'label': 'УК-1 — Test'}]}
