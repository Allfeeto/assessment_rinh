from __future__ import annotations

from typing import Sequence

CLIPBOARD_SESSION_KEY = 'assessment_clipboard_item_ids'


def get_clipboard_item_ids(session) -> list[int]:
    raw = session.get(CLIPBOARD_SESSION_KEY, [])
    result = []
    for value in raw:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return result


def set_clipboard_item_ids(session, item_ids: Sequence[int]) -> None:
    unique_ids = []
    seen = set()
    for value in item_ids:
        try:
            item_id = int(value)
        except (TypeError, ValueError):
            continue
        if item_id not in seen:
            seen.add(item_id)
            unique_ids.append(item_id)
    session[CLIPBOARD_SESSION_KEY] = unique_ids
    session.modified = True


def clear_clipboard(session) -> None:
    if CLIPBOARD_SESSION_KEY in session:
        del session[CLIPBOARD_SESSION_KEY]
        session.modified = True
