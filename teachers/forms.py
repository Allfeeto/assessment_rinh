from django import forms
from django.contrib.auth import get_user_model

from core.forms import apply_autocomplete_attrs, autocomplete_queryset
from disciplines.models import ProgramDiscipline

from .models import Department, Teacher, TeacherProgramDiscipline


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ('number', 'short_name', 'full_name', 'head_teacher')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['head_teacher'].required = False
        self.fields['head_teacher'].help_text = (
            'Можно оставить пустым при создании кафедры и назначить позже.'
        )
        if self.instance and self.instance.pk:
            self.fields['head_teacher'].queryset = Teacher.objects.filter(department=self.instance).order_by('full_name')
            apply_autocomplete_attrs(
                self.fields['head_teacher'],
                kind='teacher',
                placeholder='Введите ФИО преподавателя',
                extra_params={'department_id': self.instance.id},
            )
        else:
            self.fields['head_teacher'].queryset = Teacher.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        head_teacher = cleaned_data.get('head_teacher')
        if head_teacher and self.instance and self.instance.pk and head_teacher.department_id != self.instance.id:
            self.add_error('head_teacher', 'Заведующий должен относиться к этой кафедре.')
        return cleaned_data


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ('user', 'department', 'full_name', 'academic_degree', 'academic_title')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].required = False
        selected_user_id = None
        selected_department_id = None
        if self.is_bound:
            selected_user_id = self.data.get('user')
            selected_department_id = self.data.get('department')
        elif self.instance and self.instance.pk:
            selected_user_id = self.instance.user_id
            selected_department_id = self.instance.department_id

        user_model = get_user_model()
        base_user_qs = user_model.objects.order_by('username')
        self.fields['user'].queryset = autocomplete_queryset(base_user_qs, selected_user_id)
        user_extra_params = None
        if selected_user_id and str(selected_user_id).isdigit():
            user_extra_params = {'selected_user_id': int(selected_user_id)}
        apply_autocomplete_attrs(
            self.fields['user'],
            kind='auth_user',
            placeholder='Введите username, имя или email пользователя',
            extra_params=user_extra_params,
        )

        base_department_qs = Department.objects.order_by('number')
        self.fields['department'].queryset = autocomplete_queryset(base_department_qs, selected_department_id)
        apply_autocomplete_attrs(
            self.fields['department'],
            kind='department',
            placeholder='Введите номер или название кафедры',
        )
        self.fields['academic_degree'].queryset = self.fields['academic_degree'].queryset.order_by('name')
        self.fields['academic_title'].queryset = self.fields['academic_title'].queryset.order_by('name')


class TeacherProgramDisciplineForm(forms.ModelForm):
    class Meta:
        model = TeacherProgramDiscipline
        fields = ('teacher', 'program_discipline')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_teacher_id = None
        selected_program_discipline_id = None
        if self.is_bound:
            selected_teacher_id = self.data.get('teacher')
            selected_program_discipline_id = self.data.get('program_discipline')
        elif self.instance and self.instance.pk:
            selected_teacher_id = self.instance.teacher_id
            selected_program_discipline_id = self.instance.program_discipline_id

        teacher_qs = Teacher.objects.order_by('full_name')
        self.fields['teacher'].queryset = autocomplete_queryset(teacher_qs, selected_teacher_id)
        apply_autocomplete_attrs(
            self.fields['teacher'],
            kind='teacher',
            placeholder='Введите ФИО преподавателя',
        )

        program_discipline_qs = ProgramDiscipline.objects.select_related(
            'educational_program__program_profile',
            'educational_program__department',
            'discipline',
        ).filter(educational_program__is_deleted=False).order_by(
            'educational_program__program_profile__code',
            'educational_program__admission_year',
            'discipline__name',
        )
        self.fields['program_discipline'].queryset = autocomplete_queryset(
            program_discipline_qs,
            selected_program_discipline_id,
        )
        apply_autocomplete_attrs(
            self.fields['program_discipline'],
            kind='program_discipline',
            placeholder='Введите программу или дисциплину',
        )
