from django import forms

from assessment.access import program_discipline_queryset_for_user
from assessment.services import get_ui_assessment_item_types_queryset
from competencies.models import Competence, DisciplineCompetence
from core.forms import apply_autocomplete_attrs, autocomplete_queryset
from core.form_fields import AssessmentItemTypeChoiceField, CompetenceChoiceField
from core.models import AssessmentItemType
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram


class WordExportForm(forms.Form):
    educational_program = forms.ModelChoiceField(
        queryset=EducationalProgram.objects.none(),
        required=True,
        label='Образовательная программа',
    )
    discipline = forms.ModelChoiceField(
        queryset=Discipline.objects.none(),
        required=True,
        label='Дисциплина',
    )
    assessment_item_type = AssessmentItemTypeChoiceField(
        queryset=AssessmentItemType.objects.none(),
        required=False,
        label='Тип задания',
    )
    competence = CompetenceChoiceField(
        queryset=Competence.objects.none(),
        required=False,
        label='Компетенция',
    )

    def __init__(self, *args, validate_required=True, **kwargs):
        user = kwargs.pop('user', None)
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

        program_discipline_scope = (
            program_discipline_queryset_for_user(user)
            if user is not None
            else ProgramDiscipline.objects.filter(educational_program__is_deleted=False)
        )

        base_program_qs = EducationalProgram.objects.select_related(
            'program_profile',
            'department',
        ).filter(
            is_deleted=False,
            program_disciplines__in=program_discipline_scope,
        ).distinct().order_by('program_profile__code', 'admission_year')
        self.fields['educational_program'].queryset = autocomplete_queryset(base_program_qs, program_id)
        apply_autocomplete_attrs(
            self.fields['educational_program'],
            kind='educational_program',
            placeholder='Введите профиль, кафедру или год набора',
            dynamic_params=(('id_discipline', 'discipline_id'), ('id_competence', 'competence_id')),
        )
        if not validate_required:
            self.fields['educational_program'].required = False
            self.fields['discipline'].required = False

        base_discipline_qs = Discipline.objects.filter(
            program_disciplines__in=program_discipline_scope,
        ).distinct().order_by('name')
        linked_disciplines_qs = program_discipline_scope
        if program_id:
            linked_disciplines_qs = linked_disciplines_qs.filter(educational_program_id=program_id)
        if selected_competence_id:
            linked_disciplines_qs = linked_disciplines_qs.filter(
                discipline_competences__competence_id=selected_competence_id
            )
        if program_id or selected_competence_id:
            base_discipline_qs = base_discipline_qs.filter(
                id__in=linked_disciplines_qs.values_list('discipline_id', flat=True)
            ).distinct()
        self.fields['discipline'].queryset = autocomplete_queryset(base_discipline_qs, discipline_id)
        discipline_labels = {}
        label_scope = linked_disciplines_qs.select_related('discipline').order_by('discipline__name', 'discipline_code')
        for program_discipline in label_scope:
            discipline_labels.setdefault(
                program_discipline.discipline_id,
                program_discipline.discipline_display_name,
            )
        self.fields['discipline'].label_from_instance = (
            lambda obj: discipline_labels.get(obj.id, obj.name)
        )
        apply_autocomplete_attrs(
            self.fields['discipline'],
            kind='discipline',
            placeholder='Введите наименование дисциплины',
            parent_field_id='id_educational_program',
            parent_param='educational_program_id',
            dynamic_params=(('id_competence', 'competence_id'),),
        )

        self.fields['assessment_item_type'].queryset = get_ui_assessment_item_types_queryset()

        competence_qs = Competence.objects.select_related(
            'competence_type',
            'educational_program__program_profile',
        ).filter(
            educational_program__is_deleted=False,
            educational_program__program_disciplines__in=program_discipline_scope,
        ).distinct().order_by('code')

        if program_id:
            competence_qs = competence_qs.filter(educational_program_id=program_id)

        if discipline_id:
            program_disciplines = program_discipline_scope.filter(
                discipline_id=discipline_id,
                educational_program__is_deleted=False,
            )
            if program_id:
                program_disciplines = program_disciplines.filter(
                    educational_program_id=program_id,
                )
            linked_ids = DisciplineCompetence.objects.filter(
                program_discipline_id__in=program_disciplines.values_list('id', flat=True),
            ).values_list('competence_id', flat=True)
            competence_qs = competence_qs.filter(id__in=linked_ids)

        self.fields['competence'].queryset = competence_qs
        apply_autocomplete_attrs(
            self.fields['competence'],
            kind='competence',
            placeholder='Введите код или наименование компетенции',
            parent_field_id='id_educational_program',
            parent_param='educational_program_id',
            dynamic_params=(('id_discipline', 'discipline_id'),),
        )

        for field_name in ('educational_program', 'discipline', 'competence', 'assessment_item_type'):
            self.fields[field_name].widget.attrs['data-auto-submit-change'] = '1'

    def clean(self):
        cleaned_data = super().clean()
        educational_program = cleaned_data.get('educational_program')
        discipline = cleaned_data.get('discipline')
        competence = cleaned_data.get('competence')

        if not educational_program or not discipline or not competence:
            return cleaned_data
        if educational_program.is_deleted:
            self.add_error('educational_program', 'Нельзя экспортировать образовательную программу из корзины.')
            return cleaned_data

        program_discipline = ProgramDiscipline.objects.filter(
            educational_program=educational_program,
            discipline=discipline,
            educational_program__is_deleted=False,
        ).first()

        if not program_discipline:
            self.add_error('discipline', 'Выбранная дисциплина не включена в указанную образовательную программу.')
            return cleaned_data

        linked = DisciplineCompetence.objects.filter(
            program_discipline=program_discipline,
            competence=competence,
        ).exists()
        if not linked:
            self.add_error(
                'competence',
                'Выберите компетенцию, связанную с выбранной дисциплиной учебного плана.',
            )

        return cleaned_data
