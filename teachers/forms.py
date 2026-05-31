from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from core.forms import apply_autocomplete_attrs, autocomplete_queryset
from core.permissions import (
    can_assign_teacher_to_program_discipline,
    can_manage_teacher,
    filter_program_disciplines_for_assignment,
    filter_teachers_for_assignment,
    get_user_departments,
    is_senior_teacher,
    is_superuser_or_platform_admin,
    assignment_denial_reason,
)
from disciplines.models import ProgramDiscipline

from .models import Department, Teacher, TeacherProgramDiscipline


class ContainerCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    option_inherits_attrs = False


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
            self.fields['head_teacher'].queryset = (
                Teacher.objects.filter(
                    Q(department=self.instance) | Q(departments=self.instance)
                )
                .distinct()
                .order_by('full_name')
            )
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
        if (
            head_teacher
            and self.instance
            and self.instance.pk
            and head_teacher.department_id != self.instance.id
            and not head_teacher.departments.filter(pk=self.instance.id).exists()
        ):
            self.add_error('head_teacher', 'Заведующий должен относиться к этой кафедре.')
        return cleaned_data


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = (
            'user',
            'department',
            'departments',
            'full_name',
            'academic_degree',
            'academic_title',
        )
        widgets = {
            'departments': ContainerCheckboxSelectMultiple(attrs={'class': 'choice-list'}),
        }

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        self.request_user = request_user
        self._managed_department_ids = None
        self._preserved_department_ids = set()
        can_edit_user = request_user is None or is_superuser_or_platform_admin(request_user)
        if can_edit_user:
            self.fields['user'].required = False
        else:
            self.fields.pop('user', None)

        selected_user_id = None
        selected_department_id = None
        if self.is_bound:
            selected_user_id = self.data.get('user') if can_edit_user else None
            selected_department_id = self.data.get('department')
        elif self.instance and self.instance.pk:
            selected_user_id = self.instance.user_id if can_edit_user else None
            selected_department_id = self.instance.department_id

        if can_edit_user:
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
        department_extra_params = None
        if request_user is not None and is_senior_teacher(request_user) and not is_superuser_or_platform_admin(request_user):
            managed_departments = get_user_departments(request_user)
            self._managed_department_ids = set(managed_departments.values_list('id', flat=True))
            self._preserved_department_ids = set()
            if self.instance and self.instance.pk:
                existing_ids = set(self.instance.departments.values_list('id', flat=True))
                self._preserved_department_ids = existing_ids - self._managed_department_ids

            allowed_department_ids = set(self._managed_department_ids)
            if selected_department_id and str(selected_department_id).isdigit():
                selected_department_pk = int(selected_department_id)
                if self.instance and self.instance.pk and selected_department_pk == self.instance.department_id:
                    allowed_department_ids.add(selected_department_pk)
            base_department_qs = base_department_qs.filter(pk__in=allowed_department_ids)
            department_extra_params = {'purpose': 'teacher_management'}

            if len(self._managed_department_ids) == 1 and not self.instance.pk and not selected_department_id:
                only_department_id = next(iter(self._managed_department_ids))
                self.initial.setdefault('department', only_department_id)
                selected_department_id = only_department_id

        self.fields['department'].queryset = autocomplete_queryset(base_department_qs, selected_department_id)
        if (
            self.instance
            and self.instance.pk
            and self._managed_department_ids is not None
            and self.instance.department_id not in self._managed_department_ids
        ):
            self.fields['department'].disabled = True
            self.fields['department'].help_text = (
                'Основная кафедра не входит в ваши кафедры управления и сохраняется без изменений.'
            )
        apply_autocomplete_attrs(
            self.fields['department'],
            kind='department',
            placeholder='Введите номер или название основной кафедры',
            extra_params=department_extra_params,
        )
        self.fields['departments'].required = False
        departments_qs = Department.objects.order_by('number')
        if self._managed_department_ids is not None:
            departments_qs = departments_qs.filter(pk__in=self._managed_department_ids)
        self.fields['departments'].queryset = departments_qs
        self.fields['departments'].help_text = (
            'Выберите все кафедры преподавателя. Основная кафедра будет добавлена автоматически.'
        )
        self.fields['academic_degree'].queryset = self.fields['academic_degree'].queryset.order_by('name')
        self.fields['academic_title'].queryset = self.fields['academic_title'].queryset.order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        if self.request_user is None or is_superuser_or_platform_admin(self.request_user):
            return cleaned_data

        if not is_senior_teacher(self.request_user):
            self.add_error(None, 'Недостаточно прав для изменения преподавателя.')
            return cleaned_data

        if self.instance and self.instance.pk and not can_manage_teacher(self.request_user, self.instance):
            self.add_error(None, 'Нельзя изменить преподавателя: он не относится к вашим кафедрам.')
            return cleaned_data

        managed_department_ids = self._managed_department_ids or set()
        if not managed_department_ids:
            self.add_error(None, 'Для вашей учётной записи не указаны кафедры управления.')
            return cleaned_data

        department = cleaned_data.get('department')
        if department and department.id not in managed_department_ids:
            if not (
                self.instance
                and self.instance.pk
                and department.id == self.instance.department_id
                and self.fields['department'].disabled
            ):
                self.add_error('department', 'Нельзя создать преподавателя в выбранной кафедре.')

        for department in cleaned_data.get('departments') or []:
            if department.id not in managed_department_ids:
                self.add_error('departments', 'Нельзя добавить преподавателю чужую кафедру.')
                break

        return cleaned_data

    def _save_m2m(self):
        super()._save_m2m()
        if self._managed_department_ids is None or not self.instance.pk:
            return

        department_ids = set(self.instance.departments.values_list('id', flat=True))
        department_ids.update(self._preserved_department_ids)
        if self.instance.department_id:
            department_ids.add(self.instance.department_id)
        self.instance.departments.set(department_ids)

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            instance.ensure_primary_department_membership()
        return instance


class TeacherProgramDisciplineForm(forms.ModelForm):
    class Meta:
        model = TeacherProgramDiscipline
        fields = ('teacher', 'program_discipline')

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
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
        if self.request_user is not None:
            teacher_qs = filter_teachers_for_assignment(self.request_user, teacher_qs)
        self.fields['teacher'].queryset = autocomplete_queryset(teacher_qs, selected_teacher_id)
        apply_autocomplete_attrs(
            self.fields['teacher'],
            kind='teacher',
            placeholder='Введите ФИО преподавателя',
            extra_params={'purpose': 'assignment'} if self.request_user is not None else None,
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
        if self.request_user is not None:
            program_discipline_qs = filter_program_disciplines_for_assignment(
                self.request_user,
                program_discipline_qs,
            )
        self.fields['program_discipline'].queryset = autocomplete_queryset(
            program_discipline_qs,
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

    def clean(self):
        cleaned_data = super().clean()
        if self.request_user is None:
            return cleaned_data

        teacher = cleaned_data.get('teacher')
        program_discipline = cleaned_data.get('program_discipline')
        if teacher and program_discipline and not can_assign_teacher_to_program_discipline(
            self.request_user,
            teacher,
            program_discipline,
        ):
            self.add_error(
                None,
                assignment_denial_reason(self.request_user, teacher, program_discipline),
            )
        return cleaned_data
