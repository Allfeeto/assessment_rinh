from django import forms

from .models import Department, Teacher


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ('number', 'short_name', 'full_name', 'head_teacher')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['head_teacher'].queryset = Teacher.objects.filter(department=self.instance).order_by('full_name')
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
        self.fields['department'].queryset = self.fields['department'].queryset.order_by('number')
        self.fields['academic_degree'].queryset = self.fields['academic_degree'].queryset.order_by('name')
        self.fields['academic_title'].queryset = self.fields['academic_title'].queryset.order_by('name')
