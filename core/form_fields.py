"""
Общие поля форм, дублировавшиеся в assessment/forms.py, export/forms.py
и reports/forms.py. Сюда же стоит выносить любые универсальные
ModelChoiceField/ModelMultipleChoiceField, чтобы не плодить копии.
"""
from __future__ import annotations

from django import forms

from assessment.services import get_item_type_ui_name


class AssessmentItemTypeChoiceField(forms.ModelChoiceField):
    """Подписи в выпадашке — человекочитаемые названия типов задания."""

    def label_from_instance(self, obj):
        return get_item_type_ui_name(obj)


class CompetenceChoiceField(forms.ModelChoiceField):
    """`Код — Наименование` для одиночного выбора компетенции."""

    def label_from_instance(self, obj):
        return f'{obj.code} — {obj.name}'


class CompetenceMultipleChoiceField(forms.ModelMultipleChoiceField):
    """`Код — Наименование` для множественного выбора компетенций."""

    def label_from_instance(self, obj):
        return f'{obj.code} — {obj.name}'
