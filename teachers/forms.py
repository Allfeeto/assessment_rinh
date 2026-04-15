from django import forms

from core.forms import apply_autocomplete_attrs, autocomplete_queryset

from .models import Department, Teacher


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
        fields = ('department', 'full_name', 'academic_degree', 'academic_title')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_department_id = None
        if self.is_bound:
            selected_department_id = self.data.get('department')
        elif self.instance and self.instance.pk:
            selected_department_id = self.instance.department_id

        base_department_qs = Department.objects.order_by('number')
        self.fields['department'].queryset = autocomplete_queryset(base_department_qs, selected_department_id)
        apply_autocomplete_attrs(
            self.fields['department'],
            kind='department',
            placeholder='Введите номер или название кафедры',
        )
        self.fields['academic_degree'].queryset = self.fields['academic_degree'].queryset.order_by('name')
        self.fields['academic_title'].queryset = self.fields['academic_title'].queryset.order_by('name')
