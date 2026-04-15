from django import forms

from assessment.services import get_item_type_ui_name
from competencies.models import Competence, DisciplineCompetence
from core.models import AssessmentItemType
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram


class AssessmentItemTypeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return get_item_type_ui_name(obj.name)


class CompetenceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.code} — {obj.name}'


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
    competence = CompetenceChoiceField(
        queryset=Competence.objects.none(),
        required=False,
        label='Компетенция',
    )
    assessment_item_type = AssessmentItemTypeChoiceField(
        queryset=AssessmentItemType.objects.none(),
        required=False,
        label='Тип задания',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['educational_program'].queryset = EducationalProgram.objects.select_related(
            'program_profile',
            'department',
        ).order_by('program_profile__code', 'admission_year')
        self.fields['discipline'].queryset = Discipline.objects.order_by('name')
        self.fields['assessment_item_type'].queryset = AssessmentItemType.objects.order_by('name')

        competence_qs = Competence.objects.select_related(
            'competence_type',
            'educational_program__program_profile',
        ).order_by('code')

        program_id = None
        discipline_id = None
        if self.is_bound:
            program_id = self.data.get('educational_program')
            discipline_id = self.data.get('discipline')
        else:
            program = self.initial.get('educational_program')
            discipline = self.initial.get('discipline')
            program_id = program.id if hasattr(program, 'id') else program
            discipline_id = discipline.id if hasattr(discipline, 'id') else discipline

        if program_id:
            competence_qs = competence_qs.filter(educational_program_id=program_id)

        if program_id and discipline_id:
            program_discipline = ProgramDiscipline.objects.filter(
                educational_program_id=program_id,
                discipline_id=discipline_id,
            ).first()
            if program_discipline:
                linked_ids = DisciplineCompetence.objects.filter(
                    program_discipline=program_discipline,
                ).values_list('competence_id', flat=True)
                competence_qs = competence_qs.filter(id__in=linked_ids)
            else:
                competence_qs = competence_qs.none()

        self.fields['competence'].queryset = competence_qs
