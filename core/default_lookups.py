from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Q

from .lookups import (
    apply_lookup_tokens,
    filter_selected_id,
    register_lookup,
    unique_lookup_results,
)
from .models import AssessmentItemType
from .permissions import is_staff_or_superuser


def lookup_auth_user(request, query, selected_id, limit):
    if not is_staff_or_superuser(request.user):
        return []

    user_model = get_user_model()
    queryset = user_model.objects.order_by('username')
    selected_user_id = request.GET.get('selected_user_id')
    if selected_user_id and selected_user_id.isdigit():
        queryset = queryset.filter(Q(teacher_profile__isnull=True) | Q(id=int(selected_user_id)))
    else:
        queryset = queryset.filter(teacher_profile__isnull=True)
    if query:
        queryset = apply_lookup_tokens(queryset, query, ('username', 'first_name', 'last_name', 'email'))
    queryset = filter_selected_id(queryset, selected_id)
    results = []
    seen_ids = set()
    for obj in queryset:
        if obj.id in seen_ids:
            continue
        seen_ids.add(obj.id)
        display_name = ' '.join(part for part in [obj.last_name, obj.first_name] if part).strip()
        label = f'{obj.username} ({display_name})' if display_name else obj.username
        results.append({'id': obj.id, 'label': label})
        if limit is not None and len(results) >= limit:
            break
    return results


def lookup_assessment_item_type(request, query, selected_id, limit):
    queryset = AssessmentItemType.objects.order_by('code', 'name')
    if query:
        queryset = apply_lookup_tokens(queryset, query, ('code', 'name'))
    queryset = filter_selected_id(queryset, selected_id)
    return unique_lookup_results(queryset, limit, lambda obj: obj.name)


def register_core_lookups() -> None:
    register_lookup('auth_user', lookup_auth_user)
    register_lookup('assessment_item_type', lookup_assessment_item_type)
