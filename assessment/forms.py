from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from competencies.models import Competence

from .models import AssessmentItem, AssessmentItemRow
from .services import get_assessment_item_competence_ids, sync_assessment_item_competences


ITEM_TYPE_SINGLE = 'single_choice'
ITEM_TYPE_MULTIPLE = 'multiple_choice'
ITEM_TYPE_MATCHING = 'matching'
ITEM_TYPE_SEQUENCE = 'sequence'
ITEM_TYPE_OPEN = 'open_answer'


def normalize_item_type_name(name):
    return (name or '').strip().lower()


class AssessmentItemForm(forms.ModelForm):
    competences = forms.ModelMultipleChoiceField(
        queryset=Competence.objects.none(),
        required=False,
        label='Проверяемые компетенции',
        widget=forms.SelectMultiple(
            attrs={
                'size': 8,
                'data-fetch-url': '/competencies/by-program-discipline/?program_discipline_id={value}',
            }
        ),
    )

    class Meta:
        model = AssessmentItem
        fields = (
            'program_discipline',
            'assessment_item_type',
            'prompt_text',
            'instruction_text',
            'left_column_title',
            'right_column_title',
            'competences',
        )
        widgets = {
            'program_discipline': forms.Select(attrs={'data-dependent-child': 'id_competences'}),
            'prompt_text': forms.Textarea(attrs={'rows': 4}),
            'instruction_text': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['program_discipline'].queryset = self.fields['program_discipline'].queryset.select_related(
            'educational_program__program_profile',
            'discipline',
        ).order_by(
            'educational_program__program_profile__code',
            'educational_program__admission_year',
            'discipline__name',
        )
        self.fields['assessment_item_type'].queryset = self.fields['assessment_item_type'].queryset.order_by('name')

        program_discipline_id = None
        if self.is_bound:
            program_discipline_id = self.data.get('program_discipline')
        elif self.instance and self.instance.pk:
            program_discipline_id = self.instance.program_discipline_id

        competence_qs = Competence.objects.select_related('competence_type').order_by('code')
        if program_discipline_id:
            educational_program_id = (
                self.fields['program_discipline'].queryset
                .filter(pk=program_discipline_id)
                .values_list('educational_program_id', flat=True)
                .first()
            )
            if educational_program_id:
                competence_qs = competence_qs.filter(educational_program_id=educational_program_id)

        self.fields['competences'].queryset = competence_qs

        if self.instance and self.instance.pk and not self.is_bound:
            self.fields['competences'].initial = get_assessment_item_competence_ids(self.instance.pk)

    def clean(self):
        cleaned_data = super().clean()
        program_discipline = cleaned_data.get('program_discipline')
        competences = cleaned_data.get('competences')

        if program_discipline and competences:
            invalid_competence_ids = [
                competence.id
                for competence in competences
                if competence.educational_program_id != program_discipline.educational_program_id
            ]
            if invalid_competence_ids:
                self.add_error('competences', 'Выбраны компетенции из другого учебного плана.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)
        self._competence_ids = list(
            self.cleaned_data.get('competences', Competence.objects.none()).values_list('id', flat=True)
        )

        if commit and instance.pk:
            sync_assessment_item_competences(instance.pk, self._competence_ids)

        return instance

    def save_m2m(self):
        super().save_m2m()
        if self.instance.pk:
            sync_assessment_item_competences(self.instance.pk, getattr(self, '_competence_ids', []))


class AssessmentItemRowForm(forms.ModelForm):
    class Meta:
        model = AssessmentItemRow
        fields = (
            'row_kind',
            'left_label',
            'left_text',
            'right_label',
            'right_text',
            'sort_order',
            'correct_order',
            'is_correct',
            'open_answer_text',
        )
        widgets = {
            'left_label': forms.TextInput(attrs={'placeholder': 'например: А'}),
            'right_label': forms.TextInput(attrs={'placeholder': 'например: 1'}),
            'left_text': forms.Textarea(attrs={'rows': 2}),
            'right_text': forms.Textarea(attrs={'rows': 2}),
            'open_answer_text': forms.Textarea(attrs={'rows': 2}),
            'sort_order': forms.NumberInput(attrs={'min': 1}),
            'correct_order': forms.NumberInput(attrs={'min': 1}),
        }


class BaseAssessmentItemRowFormSet(BaseInlineFormSet):
    item_type_name = ''

    @staticmethod
    def _row_has_content(cleaned_data):
        content_fields = (
            'left_label',
            'left_text',
            'right_label',
            'right_text',
            'sort_order',
            'correct_order',
            'is_correct',
            'open_answer_text',
        )
        return any(cleaned_data.get(field) not in (None, '', False) for field in content_fields)

    def _active_rows(self):
        rows = []
        for form in self.forms:
            cleaned_data = getattr(form, 'cleaned_data', None)
            if not cleaned_data or cleaned_data.get('DELETE'):
                continue
            if self._row_has_content(cleaned_data):
                rows.append(cleaned_data)
        return rows

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        item_type = normalize_item_type_name(self.item_type_name)
        rows = self._active_rows()

        if item_type in {ITEM_TYPE_SINGLE, ITEM_TYPE_MULTIPLE}:
            for row in rows:
                row['row_kind'] = AssessmentItemRow.KIND_OPTION
            option_rows = [row for row in rows if row.get('left_text')]
            if len(option_rows) < 2:
                raise ValidationError('Для заданий с выбором должно быть минимум 2 варианта ответа.')
            correct_count = sum(1 for row in option_rows if row.get('is_correct'))
            if item_type == ITEM_TYPE_SINGLE and correct_count != 1:
                raise ValidationError('Для single_choice нужен ровно 1 правильный вариант.')
            if item_type == ITEM_TYPE_MULTIPLE and correct_count < 1:
                raise ValidationError('Для multiple_choice нужен минимум 1 правильный вариант.')

        elif item_type == ITEM_TYPE_MATCHING:
            pair_rows = []
            right_distractors = []
            for row in rows:
                row_kind = row.get('row_kind') or AssessmentItemRow.KIND_MATCH_PAIR
                row['row_kind'] = row_kind
                if row_kind == AssessmentItemRow.KIND_MATCH_PAIR:
                    pair_rows.append(row)
                elif row_kind == AssessmentItemRow.KIND_MATCH_RIGHT_DISTRACTOR:
                    right_distractors.append(row)
                else:
                    raise ValidationError('Для matching допустимы только match_pair и match_right_distractor.')

            if len(pair_rows) < 1:
                raise ValidationError('Для matching нужна минимум 1 корректная пара.')

            for row in pair_rows:
                if not row.get('left_text') or not row.get('right_text'):
                    raise ValidationError('Для пары соответствия заполните левый и правый текст.')

            for row in right_distractors:
                if not row.get('right_text'):
                    raise ValidationError('Для правого дистрактора заполните right_text.')

            sort_orders = [row.get('sort_order') for row in rows if row.get('sort_order')]
            if len(sort_orders) != len(set(sort_orders)):
                raise ValidationError('sort_order в matching должен быть уникальным.')

        elif item_type == ITEM_TYPE_SEQUENCE:
            for row in rows:
                row['row_kind'] = AssessmentItemRow.KIND_SEQUENCE
            sequence_rows = [row for row in rows if row.get('left_text')]
            if len(sequence_rows) < 2:
                raise ValidationError('Для sequence нужно минимум 2 элемента.')
            orders = [row.get('correct_order') for row in sequence_rows]
            if any(order in (None, '') for order in orders):
                raise ValidationError('Для sequence укажите correct_order для всех элементов.')
            if len(orders) != len(set(orders)):
                raise ValidationError('correct_order должен быть уникальным внутри задания.')
            sorted_orders = sorted(orders)
            if sorted_orders != list(range(1, len(sorted_orders) + 1)):
                raise ValidationError('correct_order должен задавать непрерывный порядок от 1 до N.')

        elif item_type == ITEM_TYPE_OPEN:
            for row in rows:
                row['row_kind'] = AssessmentItemRow.KIND_OPEN_ANSWER
            open_rows = [row for row in rows if row.get('open_answer_text')]
            if len(open_rows) < 1:
                raise ValidationError('Для open_answer нужен минимум 1 допустимый ответ.')


AssessmentItemRowFormSet = inlineformset_factory(
    AssessmentItem,
    AssessmentItemRow,
    form=AssessmentItemRowForm,
    formset=BaseAssessmentItemRowFormSet,
    extra=8,
    can_delete=True,
)
