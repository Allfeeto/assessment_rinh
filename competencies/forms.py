from django import forms

from core.forms import apply_autocomplete_attrs, autocomplete_queryset
from core.permissions import (
    can_manage_program_discipline,
    filter_program_disciplines_for_assignment,
    is_senior_teacher,
    is_superuser_or_platform_admin,
)
from disciplines.models import ProgramDiscipline
from programs.models import EducationalProgram

from .models import Competence, DisciplineCompetence


class CompetenceForm(forms.ModelForm):
    class Meta:
        model = Competence
        fields = ('educational_program', 'competence_type', 'code', 'name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_program_id = None
        if self.is_bound:
            selected_program_id = self.data.get('educational_program')
        elif self.instance and self.instance.pk:
            selected_program_id = self.instance.educational_program_id

        base_program_qs = EducationalProgram.objects.select_related(
            'program_profile',
            'department',
        ).filter(is_deleted=False).order_by('program_profile__code', 'admission_year')
        self.fields['educational_program'].queryset = autocomplete_queryset(base_program_qs, selected_program_id)
        apply_autocomplete_attrs(
            self.fields['educational_program'],
            kind='educational_program',
            placeholder='Введите профиль, кафедру или год набора',
        )
        self.fields['competence_type'].queryset = self.fields['competence_type'].queryset.order_by('name')


class DisciplineCompetenceForm(forms.ModelForm):
    class Meta:
        model = DisciplineCompetence
        fields = ('program_discipline', 'competence')

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        selected_program_discipline_id = None
        selected_competence_id = None
        if self.is_bound:
            selected_program_discipline_id = self.data.get('program_discipline')
            selected_competence_id = self.data.get('competence')
        elif self.instance and self.instance.pk:
            selected_program_discipline_id = self.instance.program_discipline_id
            selected_competence_id = self.instance.competence_id

        base_program_discipline_qs = ProgramDiscipline.objects.select_related(
            'educational_program__program_profile',
            'discipline',
        ).filter(educational_program__is_deleted=False).order_by(
            'educational_program__program_profile__code',
            'educational_program__admission_year',
            'discipline__name',
        )
        if self.request_user is not None:
            base_program_discipline_qs = filter_program_disciplines_for_assignment(
                self.request_user,
                base_program_discipline_qs,
            )
        self.fields['program_discipline'].queryset = autocomplete_queryset(
            base_program_discipline_qs,
            selected_program_discipline_id,
        )
        self.fields['program_discipline'].label_from_instance = (
            lambda obj: f'{obj.educational_program} | {obj.discipline_display_name}'
        )
        apply_autocomplete_attrs(
            self.fields['program_discipline'],
            kind='program_discipline',
            placeholder='Введите программу или дисциплину',
            extra_params={'purpose': 'assignment'} if self.request_user is not None else None,
        )

        competence_qs = Competence.objects.none()
        if selected_program_discipline_id:
            educational_program_id = (
                base_program_discipline_qs
                .filter(pk=selected_program_discipline_id)
                .values_list('educational_program_id', flat=True)
                .first()
            )
            if educational_program_id:
                competence_qs = (
                    Competence.objects.select_related('competence_type')
                    .filter(educational_program_id=educational_program_id, educational_program__is_deleted=False)
                    .order_by('code')
                )

        if selected_competence_id and not competence_qs.filter(pk=selected_competence_id).exists():
            competence_qs = Competence.objects.filter(
                pk=selected_competence_id,
                educational_program__is_deleted=False,
            )

        self.fields['competence'].queryset = competence_qs
        apply_autocomplete_attrs(
            self.fields['competence'],
            kind='competence',
            placeholder='Введите код или наименование компетенции',
            parent_field_id='id_program_discipline',
            parent_param='program_discipline_id',
            parent_required=True,
        )

    def clean(self):
        cleaned_data = super().clean()
        program_discipline = cleaned_data.get('program_discipline')
        competence = cleaned_data.get('competence')
        if program_discipline and competence:
            if program_discipline.educational_program.is_deleted:
                self.add_error('program_discipline', 'Нельзя менять матрицу программы из корзины.')
            if program_discipline.educational_program_id != competence.educational_program_id:
                self.add_error('competence', 'Компетенция должна быть из того же учебного плана.')
            if (
                self.request_user is not None
                and is_senior_teacher(self.request_user)
                and not is_superuser_or_platform_admin(self.request_user)
                and not can_manage_program_discipline(self.request_user, program_discipline)
            ):
                self.add_error('program_discipline', 'Нельзя изменить матрицу чужой кафедральной дисциплины.')
        return cleaned_data
