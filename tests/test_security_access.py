from types import SimpleNamespace

import pytest
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from core.middleware import AuthRateLimitMiddleware
from core.views import _lookup_auth_user
from core.view_helpers import NamedCreateView
from teachers.models import Department
from teachers.views import TeacherAssignmentToggleView


def _regular_user(**overrides):
    attrs = {
        'is_authenticated': True,
        'is_staff': False,
        'is_superuser': False,
        'has_perm': lambda permission: False,
        'has_perms': lambda permissions: False,
    }
    attrs.update(overrides)
    return SimpleNamespace(**attrs)


def test_regular_teacher_cannot_self_assign_program_discipline():
    request = RequestFactory().post(
        '/teachers/assignments/toggle/',
        {
            'teacher_id': '1',
            'program_discipline_id': '99',
            'assign': '1',
        },
    )
    request.user = _regular_user()

    with pytest.raises(PermissionDenied):
        TeacherAssignmentToggleView().post(request)


def test_named_crud_create_requires_staff_or_model_permission():
    class DepartmentCreateView(NamedCreateView):
        model = Department
        fields = ('number', 'short_name', 'full_name')
        list_url_name = 'teachers_department_list'

    request = RequestFactory().get('/teachers/departments/create/')
    request.user = _regular_user()
    view = DepartmentCreateView()
    view.request = request

    assert view.has_permission() is False


def test_auth_user_lookup_is_staff_only():
    request = SimpleNamespace(user=_regular_user(), GET={})

    assert _lookup_auth_user(request, query='', selected_id=None, limit=20) == []


@override_settings(
    AUTH_RATE_LIMIT_ENABLED=True,
    AUTH_RATE_LIMIT_ATTEMPTS=2,
    AUTH_RATE_LIMIT_WINDOW_SECONDS=60,
    AUTH_RATE_LIMIT_PATHS=('/accounts/login/',),
)
def test_auth_rate_limit_blocks_repeated_failed_login_attempts():
    cache.clear()

    def failed_login_response(request):
        return HttpResponse('invalid credentials', status=200)

    middleware = AuthRateLimitMiddleware(failed_login_response)
    factory = RequestFactory()

    first = middleware(
        factory.post('/accounts/login/', {'username': 'alice'}, REMOTE_ADDR='192.0.2.10')
    )
    second = middleware(
        factory.post('/accounts/login/', {'username': 'alice'}, REMOTE_ADDR='192.0.2.10')
    )
    blocked = middleware(
        factory.post('/accounts/login/', {'username': 'alice'}, REMOTE_ADDR='192.0.2.10')
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert blocked.status_code == 429
