from django import forms

from core.forms import apply_autocomplete_attrs, autocomplete_queryset

from .models import (
    MAX_ADMISSION_YEAR,
    MIN_ADMISSION_YEAR,
    EducationalProgram,
    ProgramProfile,
    TrainingDirection,
)


class TrainingDirectionForm(forms.ModelForm):
    class Meta:
        model = TrainingDirection
        fields = ('education_level', 'code', 'name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['education_level'].queryset = self.fields['education_level'].queryset.order_by('name')


class ProgramProfileForm(forms.ModelForm):
    class Meta:
        model = ProgramProfile
        fields = ('training_direction', 'code', 'name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_direction_id = None
        if self.is_bound:
            selected_direction_id = self.data.get('training_direction')
        elif self.instance and self.instance.pk:
            selected_direction_id = self.instance.training_direction_id

        base_direction_qs = TrainingDirection.objects.order_by('code')
        self.fields['training_direction'].queryset = autocomplete_queryset(base_direction_qs, selected_direction_id)
        apply_autocomplete_attrs(
            self.fields['training_direction'],
            kind='training_direction',
            placeholder='Введите код или наименование направления',
        )

    def clean(self):
        cleaned_data = super().clean()
        training_direction = cleaned_data.get('training_direction')
        code = (cleaned_data.get('code') or '').strip()
        direction_code = (getattr(training_direction, 'code', '') or '').strip()
        if direction_code and code and not code.startswith(f'{direction_code}.'):
            self.add_error(
                'code',
                f'Код профиля должен начинаться с кода направления "{direction_code}.".',
            )
        return cleaned_data


class EducationalProgramForm(forms.ModelForm):
    class Meta:
        model = EducationalProgram
        fields = ('program_profile', 'department', 'admission_year')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        selected_profile_id = None
        selected_department_id = None
        if self.is_bound:
            selected_profile_id = self.data.get('program_profile')
            selected_department_id = self.data.get('department')
        elif self.instance and self.instance.pk:
            selected_profile_id = self.instance.program_profile_id
            selected_department_id = self.instance.department_id

        base_profile_qs = ProgramProfile.objects.select_related('training_direction').order_by('code')
        self.fields['program_profile'].queryset = autocomplete_queryset(base_profile_qs, selected_profile_id)
        apply_autocomplete_attrs(
            self.fields['program_profile'],
            kind='program_profile',
            placeholder='Введите код или название профиля',
        )

        base_department_qs = self.fields['department'].queryset.order_by('number')
        self.fields['department'].queryset = autocomplete_queryset(base_department_qs, selected_department_id)
        apply_autocomplete_attrs(
            self.fields['department'],
            kind='department',
            placeholder='Введите номер или название кафедры',
        )

        self.fields['program_profile'].help_text = (
            'Направление определяется автоматически по выбранному профилю.'
        )

    def clean(self):
        cleaned_data = super().clean()
        program_profile = cleaned_data.get('program_profile')
        department = cleaned_data.get('department')
        admission_year = cleaned_data.get('admission_year')

        if admission_year is not None and not (
            MIN_ADMISSION_YEAR <= admission_year <= MAX_ADMISSION_YEAR
        ):
            self.add_error(
                'admission_year',
                f'Год набора должен быть в диапазоне {MIN_ADMISSION_YEAR}-{MAX_ADMISSION_YEAR}.',
            )

        if program_profile and department and admission_year is not None:
            duplicate = EducationalProgram.objects.active().filter(
                program_profile=program_profile,
                department=department,
                admission_year=admission_year,
            )
            if self.instance and self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                self.add_error(
                    None,
                    'Активная образовательная программа с таким профилем, кафедрой и годом набора уже существует.',
                )

        return cleaned_data


class PlxImportUploadForm(forms.Form):
    plx_file = forms.FileField(label='Файл учебного плана (.plx)')
