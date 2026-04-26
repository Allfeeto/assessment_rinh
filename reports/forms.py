from django import forms

from assessment.services import get_ui_assessment_item_types_queryset
from competencies.models import Competence, DisciplineCompetence
from core.forms import apply_autocomplete_attrs, autocomplete_queryset
from core.form_fields import AssessmentItemTypeChoiceField, CompetenceChoiceField
from core.models import AssessmentItemType
from disciplines.models import Discipline, ProgramDiscipline
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

        program_id = None
        discipline_id = None
        selected_competence_id = None
        if self.is_bound:
            program_id = self.data.get('educational_program')
            discipline_id = self.data.get('discipline')
            selected_competence_id = self.data.get('competence')
        else:
            program = self.initial.get('educational_program')
            discipline = self.initial.get('discipline')
            competence = self.initial.get('competence')
            program_id = program.id if hasattr(program, 'id') else program
            discipline_id = discipline.id if hasattr(discipline, 'id') else discipline
            selected_competence_id = competence.id if hasattr(competence, 'id') else competence

        base_program_qs = EducationalProgram.objects.select_related(
            'program_profile',
            'department',
        ).order_by('program_profile__code', 'admission_year')
        self.fields['educational_program'].queryset = autocomplete_queryset(base_program_qs, program_id)
        apply_autocomplete_attrs(
            self.fields['educational_program'],
            kind='educational_program',
            placeholder='Введите профиль, кафедру или год набора',
            dynamic_params=(('id_discipline', 'discipline_id'), ('id_competence', 'competence_id')),
        )

        base_discipline_qs = Discipline.objects.order_by('name')
        self.fields['discipline'].queryset = autocomplete_queryset(base_discipline_qs, discipline_id)
        apply_autocomplete_attrs(
            self.fields['discipline'],
            kind='discipline',
            placeholder='Введите наименование дисциплины',
            parent_field_id='id_educational_program',
            parent_param='educational_program_id',
            dynamic_params=(('id_competence', 'competence_id'),),
        )

        self.fields['assessment_item_type'].queryset = get_ui_assessment_item_types_queryset()
        self.fields['assessment_item_type'].widget.attrs['data-auto-submit-change'] = '1'

        competence_qs = Competence.objects.select_related(
            'competence_type',
            'educational_program__program_profile',
        ).order_by('code')

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
        elif discipline_id:
            linked_ids = DisciplineCompetence.objects.filter(
                program_discipline__discipline_id=discipline_id,
            ).values_list('competence_id', flat=True)
            competence_qs = competence_qs.filter(id__in=linked_ids)

        if selected_competence_id and not competence_qs.filter(pk=selected_competence_id).exists():
            competence_qs = Competence.objects.filter(pk=selected_competence_id) | competence_qs

        self.fields['competence'].queryset = competence_qs
        apply_autocomplete_attrs(
            self.fields['competence'],
            kind='competence',
            placeholder='Введите код или наименование компетенции',
            parent_field_id='id_educational_program',
            parent_param='educational_program_id',
            dynamic_params=(('id_discipline', 'discipline_id'),),
        )

        for field_name in ('educational_program', 'discipline', 'competence'):
            self.fields[field_name].widget.attrs['data-auto-submit-change'] = '1'
