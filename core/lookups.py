from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from django.db.models import Q

from .permissions import is_domain_manager


LookupResult = dict[str, Any]
LookupBuilder = Callable[[Any, str, str | None, int | None], list[LookupResult]]

LOOKUP_STOP_WORDS = {'набор', 'года', 'год', 'программа', 'профиль'}
LOOKUP_SPLIT_RE = r'[\s|,;:()«»"\'/\\\-\u2010-\u2015]+'

_LOOKUP_BUILDERS: dict[str, LookupBuilder] = {}


def register_lookup(kind: str, builder: LookupBuilder) -> None:
    normalized = (kind or '').strip()
    if not normalized:
        raise ValueError('Lookup kind must not be empty.')
    _LOOKUP_BUILDERS[normalized] = builder


def get_lookup_builder(kind: str) -> LookupBuilder | None:
    return _LOOKUP_BUILDERS.get((kind or '').strip())


def registered_lookup_kinds() -> tuple[str, ...]:
    return tuple(sorted(_LOOKUP_BUILDERS))


def normalize_lookup_limit(raw_value, *, default: int = 20, maximum: int = 50) -> int:
    try:
        limit = int(raw_value)
    except (TypeError, ValueError):
        limit = default
    return max(1, min(limit, maximum))


def tokenize_lookup_query(query: str) -> list[str]:
    if not query:
        return []
    tokens = re.split(LOOKUP_SPLIT_RE, query.replace('ё', 'е').replace('Ё', 'Е'))
    cleaned = []
    for token in tokens:
        value = token.strip().lower()
        if not value or value in LOOKUP_STOP_WORDS:
            continue
        cleaned.append(value)
    return cleaned


def apply_lookup_tokens(queryset, query, fields):
    tokens = tokenize_lookup_query(query)
    if not tokens and query:
        tokens = [query.strip().lower()]
    for token in tokens:
        conditions = Q()
        for field in fields:
            conditions |= Q(**{f'{field}__icontains': token})
        queryset = queryset.filter(conditions)
    return queryset


def filter_selected_id(queryset, selected_id):
    if selected_id and selected_id.isdigit():
        return queryset.filter(pk=int(selected_id))
    return queryset


def unique_lookup_results(queryset, limit, label_factory, key_factory=None):
    results = []
    seen_keys = set()
    for obj in queryset:
        key = key_factory(obj) if key_factory else obj.id
        if key in seen_keys:
            continue
        seen_keys.add(key)
        results.append({'id': obj.id, 'label': label_factory(obj)})
        if limit is not None and len(results) >= limit:
            break
    return results


def user_can_lookup_all(user) -> bool:
    return is_domain_manager(user)
