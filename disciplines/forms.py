from django import forms

from core.forms import apply_autocomplete_attrs, autocomplete_queryset
from core.permissions import (
    can_manage_program_discipline,
    get_user_departments,
    is_senior_teacher,
    is_superuser_or_platform_admin,
)
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
        fields = ('educational_program', 'discipline', 'discipline_code', 'department', 'is_active_in_plan')

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
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
        department_extra_params = None
        if (
            self.request_user is not None
            and is_senior_teacher(self.request_user)
            and not is_superuser_or_platform_admin(self.request_user)
        ):
            base_department_qs = get_user_departments(self.request_user).order_by('number')
            department_extra_params = {'purpose': 'program_discipline_management'}
        self.fields['department'].required = False
        self.fields['department'].queryset = autocomplete_queryset(
            base_department_qs,
            selected_department_id,
        )
        apply_autocomplete_attrs(
            self.fields['department'],
            kind='department',
            placeholder='Введите номер или название кафедры дисциплины',
            extra_params=department_extra_params,
        )

    def clean(self):
        cleaned_data = super().clean()
        if self.request_user is None or is_superuser_or_platform_admin(self.request_user):
            return cleaned_data

        if not is_senior_teacher(self.request_user):
            self.add_error(None, 'Недостаточно прав для изменения дисциплины учебного плана.')
            return cleaned_data

        user_departments = get_user_departments(self.request_user)
        user_department_ids = set(user_departments.values_list('id', flat=True))
        if not user_department_ids:
            self.add_error(None, 'Для вашей учётной записи не указаны кафедры управления.')
            return cleaned_data

        if self.instance and self.instance.pk and not can_manage_program_discipline(
            self.request_user,
            self.instance,
        ):
            self.add_error(None, 'Нельзя изменить дисциплину: она относится к другой кафедре.')
            return cleaned_data

        department = cleaned_data.get('department')
        if not department:
            self.add_error('department', 'Для изменения старшим преподавателем у дисциплины должна быть указана кафедра.')
        elif department.id not in user_department_ids:
            self.add_error('department', 'Нельзя изменить дисциплину: выбрана чужая кафедра.')

        return cleaned_data


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
        self.request_user = kwargs.pop('request_user', None)
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
        department_extra_params = None
        if (
            self.request_user is not None
            and is_senior_teacher(self.request_user)
            and not is_superuser_or_platform_admin(self.request_user)
        ):
            base_department_qs = get_user_departments(self.request_user).order_by('number')
            department_extra_params = {'purpose': 'program_discipline_management'}
        self.fields['department'].queryset = autocomplete_queryset(
            base_department_qs,
            selected_department_id,
        )
        apply_autocomplete_attrs(
            self.fields['department'],
            kind='department',
            placeholder='Введите номер или название кафедры дисциплины',
            extra_params=department_extra_params,
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

        if self.request_user is not None and not is_superuser_or_platform_admin(self.request_user):
            if not is_senior_teacher(self.request_user):
                self.add_error(None, 'Недостаточно прав для добавления дисциплины учебного плана.')
                return cleaned_data

            user_department_ids = set(
                get_user_departments(self.request_user).values_list('id', flat=True)
            )
            department = cleaned_data.get('department')
            if not user_department_ids:
                self.add_error(None, 'Для вашей учётной записи не указаны кафедры управления.')
            elif not department:
                self.add_error('department', 'Для добавления старшим преподавателем у дисциплины должна быть указана кафедра.')
            elif department.id not in user_department_ids:
                self.add_error('department', 'Нельзя добавить дисциплину в выбранную кафедру.')

        return cleaned_data
