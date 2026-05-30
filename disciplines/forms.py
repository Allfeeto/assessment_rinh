from django import forms

from core.forms import apply_autocomplete_attrs, autocomplete_queryset
from programs.models import EducationalProgram
from teachers.models import Department

from .models import Discipline, ProgramDiscipline


class DisciplineForm(forms.ModelForm):
    class Meta:
        model = Discipline
        fields = ('name',)


class ProgramDisciplineForm(forms.ModelForm):
    class Meta:
        model = ProgramDiscipline
        fields = ('educational_program', 'discipline', 'discipline_code', 'department')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_program_id = None
        selected_discipline_id = None
        selected_department_id = None
        if self.is_bound:
            selected_program_id = self.data.get('educational_program')
            selected_discipline_id = self.data.get('discipline')
            selected_department_id = self.data.get('department')
        elif self.instance and self.instance.pk:
            selected_program_id = self.instance.educational_program_id
            selected_discipline_id = self.instance.discipline_id
            selected_department_id = self.instance.department_id

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

        base_discipline_qs = Discipline.objects.order_by('name')
        self.fields['discipline'].queryset = autocomplete_queryset(base_discipline_qs, selected_discipline_id)
        apply_autocomplete_attrs(
            self.fields['discipline'],
            kind='discipline',
            placeholder='Введите наименование дисциплины',
        )

        base_department_qs = Department.objects.order_by('number')
        self.fields['department'].required = False
        self.fields['department'].queryset = autocomplete_queryset(
            base_department_qs,
            selected_department_id,
        )
        apply_autocomplete_attrs(
            self.fields['department'],
            kind='department',
            placeholder='Введите номер или название кафедры дисциплины',
        )


class ProgramDisciplineManageForm(forms.Form):
    educational_program = forms.ModelChoiceField(
        queryset=EducationalProgram.objects.none(),
        required=True,
        label='Образовательная программа',
    )
    discipline = forms.ModelChoiceField(
        queryset=Discipline.objects.none(),
        required=True,
        label='Дисциплина для добавления',
    )
    discipline_code = forms.CharField(
        required=False,
        label='Код дисциплины в учебном плане',
        max_length=50,
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        required=False,
        label='Кафедра дисциплины',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        selected_program_id = None
        selected_discipline_id = None
        selected_department_id = None
        if self.is_bound:
            selected_program_id = self.data.get('educational_program')
            selected_discipline_id = self.data.get('discipline')
            selected_department_id = self.data.get('department')
        else:
            selected_program_id = self.initial.get('educational_program')
            selected_discipline_id = self.initial.get('discipline')
            selected_department_id = self.initial.get('department')

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

        base_discipline_qs = Discipline.objects.order_by('name')
        self.fields['discipline'].queryset = autocomplete_queryset(base_discipline_qs, selected_discipline_id)
        apply_autocomplete_attrs(
            self.fields['discipline'],
            kind='discipline',
            placeholder='Введите наименование дисциплины',
            parent_field_id='id_educational_program',
            parent_param='exclude_program_id',
            parent_required=True,
        )

        base_department_qs = Department.objects.order_by('number')
        self.fields['department'].queryset = autocomplete_queryset(
            base_department_qs,
            selected_department_id,
        )
        apply_autocomplete_attrs(
            self.fields['department'],
            kind='department',
            placeholder='Введите номер или название кафедры дисциплины',
        )

    def clean(self):
        cleaned_data = super().clean()
        educational_program = cleaned_data.get('educational_program')
        discipline = cleaned_data.get('discipline')

        if not educational_program or not discipline:
            return cleaned_data

        if ProgramDiscipline.objects.filter(
            educational_program=educational_program,
            discipline=discipline,
        ).exists():
            self.add_error(
                'discipline',
                'Эта дисциплина уже добавлена в выбранный учебный план.',
            )

        return cleaned_data
