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