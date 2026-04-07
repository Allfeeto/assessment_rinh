from django import forms

from competencies.models import Competence
from core.models import AssessmentItemType
from disciplines.models import Discipline
from programs.models import EducationalProgram


class ReportFilterForm(forms.Form):
    educational_program = forms.ModelChoiceField(
        queryset=EducationalProgram.objects.none(),
        required=False,
        label='Образовательная программа',
    )
    discipline = forms.ModelChoiceField(
        queryset=Discipline.objects.none(),
        required=False,
        label='Дисциплина',
    )
    competence = forms.ModelChoiceField(
        queryset=Competence.objects.none(),
        required=False,
        label='Компетенция',
    )
    assessment_item_type = forms.ModelChoiceField(
        queryset=AssessmentItemType.objects.none(),
        required=False,
        label='Тип задания',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['educational_program'].queryset = EducationalProgram.objects.select_related(
            'program_profile',
            'department',
        ).order_by(
            'program_profile__code',
            'admission_year',
        )
        self.fields['discipline'].queryset = Discipline.objects.order_by('name')
        self.fields['competence'].queryset = Competence.objects.select_related(
            'competence_type',
            'educational_program__program_profile',
        ).order_by('code')
        self.fields['assessment_item_type'].queryset = AssessmentItemType.objects.order_by('name')
