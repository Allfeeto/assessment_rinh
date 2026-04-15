from urllib.parse import urlencode

from django import forms

from .models import (
    AcademicDegree,
    AcademicTitle,
    AssessmentItemType,
    CompetenceType,
    EducationLevel,
)


class EducationLevelForm(forms.ModelForm):
    class Meta:
        model = EducationLevel
        fields = ('name',)


class CompetenceTypeForm(forms.ModelForm):
    class Meta:
        model = CompetenceType
        fields = ('name',)


class AssessmentItemTypeForm(forms.ModelForm):
    class Meta:
        model = AssessmentItemType
        fields = ('name',)


class AcademicDegreeForm(forms.ModelForm):
    class Meta:
        model = AcademicDegree
        fields = ('name',)


class AcademicTitleForm(forms.ModelForm):
    class Meta:
        model = AcademicTitle
        fields = ('name',)


def autocomplete_queryset(base_queryset, selected_value):
    if selected_value in (None, ''):
        return base_queryset.none()
    try:
        selected_id = int(selected_value)
    except (TypeError, ValueError):
        return base_queryset.none()
    return base_queryset.filter(pk=selected_id)


def apply_autocomplete_attrs(
    field,
    *,
    kind,
    placeholder='Начните вводить для поиска',
    parent_field_id=None,
    parent_param=None,
    parent_required=False,
    extra_params=None,
):
    attrs = field.widget.attrs
    attrs['data-autocomplete-kind'] = kind
    attrs['data-autocomplete-url'] = '/core/lookup/'
    attrs['data-autocomplete-placeholder'] = placeholder

    if parent_field_id:
        attrs['data-autocomplete-parent'] = parent_field_id
    if parent_param:
        attrs['data-autocomplete-parent-param'] = parent_param
    if parent_required:
        attrs['data-autocomplete-parent-required'] = '1'
    if extra_params:
        attrs['data-autocomplete-extra'] = urlencode(extra_params)
