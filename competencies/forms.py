from django import forms
from django.db import transaction
from django.utils import timezone

from core.forms import apply_autocomplete_attrs, autocomplete_queryset
from core.permissions import (
    can_manage_department,
    can_manage_program_discipline,
    filter_program_disciplines_for_assignment,
    is_senior_teacher,
    is_superuser_or_platform_admin,
    get_user_departments,
)
from disciplines.models import ProgramDiscipline
from programs.models import EducationalProgram

from .models import Competence, CompetenceIndicator, DisciplineCompetence
from .services.indicator_parser import normalize_code, normalize_text
from .services.indicator_validator import EXPECTED_INDICATOR_ROLES


MANUAL_INDICATOR_SOURCE = 'Ручное редактирование'
INDICATOR_FORM_FIELDS = (
    ('indicator_know', '1', 'Знать'),
    ('indicator_can', '2', 'Уметь'),
    ('indicator_master', '3', 'Владеть'),
)


class CompetenceIndicatorImportForm(forms.Form):
    educational_program = forms.ModelChoiceField(
        queryset=EducationalProgram.objects.none(),
        label='Образовательная программа',
        help_text='Индикаторы будут сопоставлены только с компетенциями выбранной программы.',
        error_messages={
            'required': 'Выберите образовательную программу из списка подсказок.',
            'invalid_choice': 'Выберите образовательную программу из списка подсказок.',
        },
    )
    word_file = forms.FileField(
        label='Файл индикаторов (.doc или .docx)',
        widget=forms.ClearableFileInput(attrs={'accept': '.doc,.docx'}),
    )

    def __init__(self, *args, request_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        selected_program_id = self.data.get('educational_program') if self.is_bound else None
        queryset = EducationalProgram.objects.active().select_related(
            'program_profile__training_direction__education_level',
            'department',
        ).order_by('program_profile__code', 'admission_year', 'department__number')
        if request_user is not None and not is_superuser_or_platform_admin(request_user):
            queryset = queryset.filter(department__in=get_user_departments(request_user))
        self.fields['educational_program'].queryset = autocomplete_queryset(queryset, selected_program_id)
        self.fields['educational_program'].label_from_instance = lambda obj: obj.full_display_name
        apply_autocomplete_attrs(
            self.fields['educational_program'],
            kind='educational_program',
            placeholder='Введите код, название, год набора или кафедру',
            extra_params={'purpose': 'indicator_import'},
        )

    def clean_word_file(self):
        uploaded_file = self.cleaned_data['word_file']
        filename = (uploaded_file.name or '').strip().lower()
        if not filename.endswith(('.doc', '.docx')):
            raise forms.ValidationError('Поддерживаются только файлы Word с расширением .doc или .docx.')
        if uploaded_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('Размер файла Word не должен превышать 10 МБ.')
        return uploaded_file


class CompetenceForm(forms.ModelForm):
    indicator_know = forms.CharField(
        required=False,
        label='Знать',
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    indicator_can = forms.CharField(
        required=False,
        label='Уметь',
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    indicator_master = forms.CharField(
        required=False,
        label='Владеть',
        widget=forms.Textarea(attrs={'rows': 4}),
    )

    class Meta:
        model = Competence
        fields = ('educational_program', 'competence_type', 'code', 'name')
        widgets = {
            'code': forms.TextInput(),
            'name': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, request_user=None, **kwargs):
        self.request_user = request_user
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
        if self.request_user is not None and not is_superuser_or_platform_admin(self.request_user):
            base_program_qs = base_program_qs.filter(
                department__in=get_user_departments(self.request_user),
            )
        self.fields['educational_program'].queryset = autocomplete_queryset(base_program_qs, selected_program_id)
        apply_autocomplete_attrs(
            self.fields['educational_program'],
            kind='educational_program',
            placeholder='Введите профиль, кафедру или год набора',
        )
        self.fields['competence_type'].queryset = self.fields['competence_type'].queryset.order_by('name')
        self._configure_indicator_fields()

    def _configure_indicator_fields(self):
        raw_code = self.data.get('code') if self.is_bound else getattr(self.instance, 'code', '')
        competence_code = normalize_code(raw_code) or 'КОД'
        existing_by_suffix = {}
        if self.instance and self.instance.pk:
            for indicator in self.instance.indicators.all():
                suffix = normalize_code(indicator.code).rsplit('.', 1)[-1]
                if suffix in EXPECTED_INDICATOR_ROLES and suffix not in existing_by_suffix:
                    existing_by_suffix[suffix] = indicator

        for field_name, suffix, label in INDICATOR_FORM_FIELDS:
            expected_role = EXPECTED_INDICATOR_ROLES[suffix]
            self.fields[field_name].label = f'{label} ({competence_code}.{suffix})'
            self.fields[field_name].help_text = (
                f'Текст должен начинаться со слова «{expected_role}». '
                'Заполните все три позиции либо оставьте все три пустыми.'
            )
            if not self.is_bound and suffix in existing_by_suffix:
                self.initial[field_name] = existing_by_suffix[suffix].text

    def clean_educational_program(self):
        educational_program = self.cleaned_data['educational_program']
        if self.request_user is None or is_superuser_or_platform_admin(self.request_user):
            return educational_program
        if not can_manage_department(self.request_user, educational_program.department_id):
            raise forms.ValidationError('Нельзя менять компетенции программы чужой кафедры.')
        return educational_program

    def clean(self):
        cleaned_data = super().clean()
        indicator_values = {}
        for field_name, suffix, _label in INDICATOR_FORM_FIELDS:
            value = normalize_text(cleaned_data.get(field_name))
            cleaned_data[field_name] = value
            indicator_values[suffix] = value

        filled_count = sum(bool(value) for value in indicator_values.values())
        if filled_count == 0:
            return cleaned_data
        if filled_count != len(INDICATOR_FORM_FIELDS):
            for field_name, suffix, _label in INDICATOR_FORM_FIELDS:
                if not indicator_values[suffix]:
                    self.add_error(field_name, 'Заполните эту позицию или очистите все три индикатора.')
            self.add_error(None, 'Индикаторы должны быть заполнены полным набором: Знать, Уметь, Владеть.')
            return cleaned_data

        for field_name, suffix, _label in INDICATOR_FORM_FIELDS:
            expected_role = EXPECTED_INDICATOR_ROLES[suffix]
            if not indicator_values[suffix].casefold().startswith(expected_role.casefold()):
                self.add_error(
                    field_name,
                    f'Текст индикатора должен начинаться со слова «{expected_role}».',
                )
        return cleaned_data

    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)

        with transaction.atomic():
            instance = super().save(commit=True)
            self._save_indicators(instance)
        return instance

    def _save_indicators(self, competence):
        competence_code = normalize_code(competence.code)
        desired = {
            f'{competence_code}.{suffix}': self.cleaned_data[field_name]
            for field_name, suffix, _label in INDICATOR_FORM_FIELDS
            if self.cleaned_data.get(field_name)
        }
        existing_queryset = CompetenceIndicator.objects.select_for_update().filter(
            competence=competence,
        )
        if not desired:
            existing_queryset.delete()
            return

        existing = {
            indicator.code: indicator
            for indicator in existing_queryset
        }
        existing_queryset.exclude(code__in=desired).delete()

        now = timezone.now()
        to_create = []
        to_update = []
        for code, text in desired.items():
            current = existing.get(code)
            if current is None:
                to_create.append(
                    CompetenceIndicator(
                        competence=competence,
                        code=code,
                        text=text,
                        source_file=MANUAL_INDICATOR_SOURCE,
                    )
                )
                continue
            if normalize_text(current.text) == text:
                continue

            current.text = text
            current.last_import = None
            current.source_file = MANUAL_INDICATOR_SOURCE
            current.source_table_number = None
            current.source_row_number = None
            current.updated_at = now
            to_update.append(current)

        if to_create:
            CompetenceIndicator.objects.bulk_create(to_create)
        if to_update:
            CompetenceIndicator.objects.bulk_update(
                to_update,
                fields=(
                    'text',
                    'last_import',
                    'source_file',
                    'source_table_number',
                    'source_row_number',
                    'updated_at',
                ),
            )


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
