from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from core.forms import apply_autocomplete_attrs, autocomplete_queryset
from competencies.models import Competence, DisciplineCompetence
from core.models import AssessmentItemType
from disciplines.models import ProgramDiscipline

from .models import AssessmentItem, AssessmentItemRow
from .services import (
    TYPE_MATCHING,
    TYPE_MULTIPLE,
    TYPE_OPEN,
    TYPE_SEQUENCE,
    TYPE_SINGLE,
    TYPE_UNKNOWN,
    get_item_type_ui_name,
    get_ui_assessment_item_types_queryset,
    infer_item_type_code,
)


def _clean_text(value):
    if value is None:
        return ''
    return str(value).strip()


class AssessmentItemTypeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return get_item_type_ui_name(obj.name)


class CompetenceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.code} — {obj.name}'


class AssessmentItemForm(forms.ModelForm):
    assessment_item_type = AssessmentItemTypeChoiceField(
        queryset=AssessmentItemType.objects.none(),
        label='Тип задания',
    )
    competence = CompetenceChoiceField(
        queryset=Competence.objects.none(),
        required=False,
        label='Проверяемая компетенция',
        widget=forms.Select(),
    )

    class Meta:
        model = AssessmentItem
        fields = (
            'program_discipline',
            'assessment_item_type',
            'competence',
            'prompt_text',
            'left_column_title',
            'right_column_title',
        )
        widgets = {
            'prompt_text': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assessment_item_type'].queryset = get_ui_assessment_item_types_queryset()

        program_discipline_id = None
        selected_competence_id = None
        if self.is_bound:
            program_discipline_id = self.data.get('program_discipline')
            selected_competence_id = self.data.get('competence')
        elif self.instance and self.instance.pk:
            program_discipline_id = self.instance.program_discipline_id
            selected_competence_id = self.instance.competence_id

        base_program_discipline_qs = ProgramDiscipline.objects.select_related(
            'educational_program__program_profile',
            'discipline',
        ).order_by(
            'educational_program__program_profile__code',
            'educational_program__admission_year',
            'discipline__name',
        )
        self.fields['program_discipline'].queryset = autocomplete_queryset(
            base_program_discipline_qs,
            program_discipline_id,
        )
        apply_autocomplete_attrs(
            self.fields['program_discipline'],
            kind='program_discipline',
            placeholder='Введите программу или дисциплину',
        )

        competence_queryset = Competence.objects.none()
        if program_discipline_id:
            linked_competence_ids = DisciplineCompetence.objects.filter(
                program_discipline_id=program_discipline_id
            ).values_list('competence_id', flat=True)
            competence_queryset = Competence.objects.select_related('competence_type').filter(
                id__in=linked_competence_ids
            ).order_by('code')

        if selected_competence_id and not competence_queryset.filter(pk=selected_competence_id).exists():
            competence_queryset = Competence.objects.filter(pk=selected_competence_id)

        self.fields['competence'].queryset = competence_queryset
        self.fields['competence'].help_text = (
            'Доступны только компетенции, связанные с выбранной дисциплиной учебного плана.'
        )
        apply_autocomplete_attrs(
            self.fields['competence'],
            kind='competence',
            placeholder='Введите код или наименование компетенции',
            parent_field_id='id_program_discipline',
            parent_param='program_discipline_id',
            parent_required=True,
            extra_params={'linked_only': 1},
        )

        if self.instance and self.instance.pk and not self.is_bound:
            self.fields['competence'].initial = self.instance.competence_id

    def clean(self):
        cleaned_data = super().clean()
        program_discipline = cleaned_data.get('program_discipline')
        competence = cleaned_data.get('competence')
        item_type = cleaned_data.get('assessment_item_type')

        if not competence:
            self.add_error('competence', 'Выберите компетенцию, которую проверяет задание.')
            return cleaned_data

        if not program_discipline:
            return cleaned_data

        if competence.educational_program_id != program_discipline.educational_program_id:
            self.add_error(
                'competence',
                'Компетенция должна относиться к той же образовательной программе, что и дисциплина.',
            )

        link_exists = DisciplineCompetence.objects.filter(
            program_discipline=program_discipline,
            competence=competence,
        ).exists()
        if not link_exists:
            self.add_error(
                'competence',
                'Эта компетенция не связана с выбранной дисциплиной учебного плана. '
                'Сначала добавьте связь в матрице дисциплина-компетенция.',
            )

        item_type_code = infer_item_type_code(item_type.name if item_type else '')
        if item_type_code != TYPE_MATCHING:
            cleaned_data['left_column_title'] = None
            cleaned_data['right_column_title'] = None

        return cleaned_data


class AssessmentItemRowForm(forms.ModelForm):
    is_correct = forms.BooleanField(required=False, label='Верный ответ')

    class Meta:
        model = AssessmentItemRow
        fields = (
            'left_text',
            'right_text',
            'sort_order',
            'correct_order',
            'is_correct',
            'open_answer_text',
        )
        widgets = {
            'left_text': forms.Textarea(attrs={'rows': 2}),
            'right_text': forms.Textarea(attrs={'rows': 2}),
            'sort_order': forms.HiddenInput(),
            'correct_order': forms.HiddenInput(),
            'open_answer_text': forms.Textarea(attrs={'rows': 2}),
        }


class BaseAssessmentItemRowFormSet(BaseInlineFormSet):
    item_type_name = ''

    @staticmethod
    def _has_content(cleaned_data):
        return any(
            [
                _clean_text(cleaned_data.get('left_text')),
                _clean_text(cleaned_data.get('right_text')),
                _clean_text(cleaned_data.get('open_answer_text')),
                bool(cleaned_data.get('is_correct')),
            ]
        )

    def _active_rows(self):
        active = []
        for form in self.forms:
            cleaned_data = getattr(form, 'cleaned_data', None)
            if not cleaned_data or cleaned_data.get('DELETE'):
                continue
            if not self._has_content(cleaned_data):
                continue
            active.append((form, cleaned_data))
        return active

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        item_type_code = infer_item_type_code(self.item_type_name)
        active_rows = self._active_rows()

        for index, (form, cleaned_data) in enumerate(active_rows, start=1):
            form.instance.sort_order = index
            cleaned_data['sort_order'] = index

        if item_type_code == TYPE_UNKNOWN:
            raise ValidationError('Не удалось определить тип задания. Проверьте выбранный тип.')

        if item_type_code in {TYPE_SINGLE, TYPE_MULTIPLE}:
            self._validate_choice_rows(active_rows, item_type_code)
        elif item_type_code == TYPE_MATCHING:
            self._validate_matching_rows(active_rows)
        elif item_type_code == TYPE_SEQUENCE:
            self._validate_sequence_rows(active_rows)
        elif item_type_code == TYPE_OPEN:
            self._validate_open_rows(active_rows)

    def _validate_choice_rows(self, active_rows, item_type_code):
        option_rows = []

        for form, cleaned_data in active_rows:
            left_text = _clean_text(cleaned_data.get('left_text'))
            right_text = _clean_text(cleaned_data.get('right_text'))
            answer_text = _clean_text(cleaned_data.get('open_answer_text'))

            if not left_text:
                raise ValidationError('Для задания с выбором ответа укажите текст варианта.')
            if right_text or answer_text or cleaned_data.get('correct_order') not in (None, ''):
                raise ValidationError(
                    'Для задания с выбором ответа используются только текст варианта и признак верного ответа.'
                )

            form.instance.left_text = left_text
            form.instance.right_text = None
            form.instance.correct_order = None
            form.instance.open_answer_text = None
            form.instance.is_correct = bool(cleaned_data.get('is_correct'))
            option_rows.append(form.instance)

        if len(option_rows) < 2:
            raise ValidationError('Добавьте минимум два варианта ответа.')

        correct_count = sum(1 for row in option_rows if row.is_correct)
        if item_type_code == TYPE_SINGLE and correct_count != 1:
            raise ValidationError('Для задания с выбором одного ответа должен быть ровно один верный вариант.')
        if item_type_code == TYPE_MULTIPLE and correct_count < 1:
            raise ValidationError('Для задания с выбором нескольких ответов должен быть минимум один верный вариант.')

    def _validate_matching_rows(self, active_rows):
        pairs_count = 0

        for form, cleaned_data in active_rows:
            left_text = _clean_text(cleaned_data.get('left_text'))
            right_text = _clean_text(cleaned_data.get('right_text'))
            answer_text = _clean_text(cleaned_data.get('open_answer_text'))

            if not right_text:
                raise ValidationError(
                    'Для задания на соответствие в каждой строке заполните правую часть. '
                    'Для дистрактора оставьте левую часть пустой.'
                )
            if answer_text or cleaned_data.get('is_correct') or cleaned_data.get('correct_order') not in (None, ''):
                raise ValidationError(
                    'Для задания на соответствие используются только поля левой и правой части.'
                )

            if left_text:
                pairs_count += 1

            form.instance.left_text = left_text or None
            form.instance.right_text = right_text
            form.instance.correct_order = None
            form.instance.open_answer_text = None
            form.instance.is_correct = None

        if pairs_count < 1:
            raise ValidationError('Для задания на соответствие нужна минимум одна корректная пара (заполнены обе части).')

    def _validate_sequence_rows(self, active_rows):
        if len(active_rows) < 2:
            raise ValidationError('Для задания на последовательность нужно минимум два шага.')

        for index, (form, cleaned_data) in enumerate(active_rows, start=1):
            left_text = _clean_text(cleaned_data.get('left_text'))
            right_text = _clean_text(cleaned_data.get('right_text'))
            answer_text = _clean_text(cleaned_data.get('open_answer_text'))

            if not left_text:
                raise ValidationError('Для задания на последовательность заполните текст каждого шага.')
            if right_text or answer_text or cleaned_data.get('is_correct'):
                raise ValidationError(
                    'Для задания на последовательность используется только текст шага.'
                )

            form.instance.left_text = left_text
            form.instance.right_text = None
            # Верный порядок для последовательности назначается автоматически
            # в порядке заполнения строк формы.
            form.instance.correct_order = index
            form.instance.open_answer_text = None
            form.instance.is_correct = None

    def _validate_open_rows(self, active_rows):
        if not active_rows:
            raise ValidationError('Для открытого задания добавьте хотя бы один допустимый ответ.')

        for form, cleaned_data in active_rows:
            answer_text = _clean_text(cleaned_data.get('open_answer_text'))
            left_text = _clean_text(cleaned_data.get('left_text'))
            right_text = _clean_text(cleaned_data.get('right_text'))

            if not answer_text:
                raise ValidationError('Для открытого задания заполните допустимый вариант ответа в каждой строке.')
            if left_text or right_text or cleaned_data.get('is_correct') or cleaned_data.get('correct_order') not in (None, ''):
                raise ValidationError('Для открытого задания используется только поле допустимого ответа.')

            form.instance.left_text = None
            form.instance.right_text = None
            form.instance.correct_order = None
            form.instance.is_correct = None
            form.instance.open_answer_text = answer_text


AssessmentItemRowCreateFormSet = inlineformset_factory(
    AssessmentItem,
    AssessmentItemRow,
    form=AssessmentItemRowForm,
    formset=BaseAssessmentItemRowFormSet,
    extra=1,
    can_delete=True,
)

AssessmentItemRowUpdateFormSet = inlineformset_factory(
    AssessmentItem,
    AssessmentItemRow,
    form=AssessmentItemRowForm,
    formset=BaseAssessmentItemRowFormSet,
    extra=0,
    can_delete=True,
)
