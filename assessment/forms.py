from django import forms
from django.core.exceptions import ValidationError
from django.db import connection
from django.forms import (
    BaseFormSet,
    BaseInlineFormSet,
    formset_factory,
    inlineformset_factory,
)

from competencies.models import Competence
from disciplines.models import ProgramDiscipline

from .models import (
    AssessmentItem,
    AssessmentItemType,
    AssessmentOpenAnswer,
    AssessmentOption,
    AssessmentSequenceItem,
)

ITEM_TYPE_MATCHING = 'соответствие'
ITEM_TYPE_SEQUENCE = 'последовательность'
ITEM_TYPE_MULTIPLE = 'несколько'
ITEM_TYPE_SINGLE = 'один'
ITEM_TYPE_OPEN = 'открытый'


def normalize_item_type_name(name):
    return (name or '').strip().lower()


def resolve_item_type_name(item_type_id):
    try:
        if not item_type_id:
            return ''
        return normalize_item_type_name(
            AssessmentItemType.objects.only('name').get(pk=item_type_id).name
        )
    except (AssessmentItemType.DoesNotExist, TypeError, ValueError):
        return ''


def fetch_assessment_item_competence_ids(item_id):
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT competence_id FROM assessment_item_competence WHERE assessment_item_id = %s',
            [item_id],
        )
        return [row[0] for row in cursor.fetchall()]


def sync_assessment_item_competences(item_id, competence_ids):
    cleaned_competence_ids = sorted(set(competence_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            'DELETE FROM assessment_item_competence WHERE assessment_item_id = %s',
            [item_id],
        )
        if cleaned_competence_ids:
            cursor.executemany(
                'INSERT INTO assessment_item_competence (assessment_item_id, competence_id) VALUES (%s, %s)',
                [(item_id, competence_id) for competence_id in cleaned_competence_ids],
            )


class AssessmentItemForm(forms.ModelForm):
    competences = forms.ModelMultipleChoiceField(
        queryset=Competence.objects.none(),
        required=False,
        label='Компетенции',
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = AssessmentItem
        fields = ('program_discipline', 'assessment_item_type', 'text', 'competences')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending_competence_ids = []
        self._configure_competence_queryset()

        if self.instance.pk and not self.is_bound:
            competence_ids = fetch_assessment_item_competence_ids(self.instance.pk)
            self.fields['competences'].initial = competence_ids

    def _configure_competence_queryset(self):
        program_discipline_id = None
        if self.is_bound:
            program_discipline_id = self.data.get('program_discipline')
        elif self.instance.pk:
            program_discipline_id = self.instance.program_discipline_id
        else:
            program_discipline_id = self.initial.get('program_discipline')

        program_id = None
        if program_discipline_id:
            program_id = (
                ProgramDiscipline.objects.filter(pk=program_discipline_id)
                .values_list('educational_program_id', flat=True)
                .first()
            )

        queryset = Competence.objects.select_related('competence_type').order_by('code')
        if program_id:
            queryset = queryset.filter(educational_program_id=program_id)
        self.fields['competences'].queryset = queryset

    def save(self, commit=True):
        instance = super().save(commit=commit)
        self._pending_competence_ids = list(
            self.cleaned_data.get('competences', Competence.objects.none()).values_list('id', flat=True)
        )

        if commit and instance.pk:
            sync_assessment_item_competences(instance.pk, self._pending_competence_ids)

        return instance

    def save_m2m(self):
        super().save_m2m()
        if self.instance.pk:
            sync_assessment_item_competences(self.instance.pk, self._pending_competence_ids)


class ItemTypeAwareMixin:
    item_type_name = ''

    def get_item_type_name(self):
        return normalize_item_type_name(getattr(self, 'item_type_name', ''))


class BaseAssessmentOptionInlineFormSet(ItemTypeAwareMixin, BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        item_type_name = self.get_item_type_name()
        if item_type_name not in {ITEM_TYPE_SINGLE, ITEM_TYPE_MULTIPLE}:
            return

        options = []
        for form in self.forms:
            cleaned_data = getattr(form, 'cleaned_data', None)
            if not cleaned_data or cleaned_data.get('DELETE'):
                continue
            if cleaned_data.get('text'):
                options.append(cleaned_data)

        if not options:
            raise ValidationError('Для этого типа задания требуется минимум один вариант ответа.')

        correct_count = sum(1 for option in options if option.get('is_correct'))

        if item_type_name == ITEM_TYPE_SINGLE and correct_count != 1:
            raise ValidationError('Для типа "один" должен быть ровно один верный вариант.')

        if item_type_name == ITEM_TYPE_MULTIPLE and correct_count < 1:
            raise ValidationError('Для типа "несколько" должен быть минимум один верный вариант.')


class BaseAssessmentSequenceInlineFormSet(ItemTypeAwareMixin, BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        if self.get_item_type_name() != ITEM_TYPE_SEQUENCE:
            return

        sequence_items = []
        for form in self.forms:
            cleaned_data = getattr(form, 'cleaned_data', None)
            if not cleaned_data or cleaned_data.get('DELETE'):
                continue
            if cleaned_data.get('text'):
                sequence_items.append(cleaned_data)

        if not sequence_items:
            raise ValidationError('Для типа "последовательность" добавьте минимум один элемент.')

        orders = [item.get('correct_order') for item in sequence_items]
        if any(order is None for order in orders):
            raise ValidationError('Для последовательности заполните порядок для всех элементов.')

        if len(orders) != len(set(orders)):
            raise ValidationError('Для последовательности порядок должен быть уникальным.')


class BaseAssessmentOpenAnswerInlineFormSet(ItemTypeAwareMixin, BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        if self.get_item_type_name() != ITEM_TYPE_OPEN:
            return

        answers = []
        for form in self.forms:
            cleaned_data = getattr(form, 'cleaned_data', None)
            if not cleaned_data or cleaned_data.get('DELETE'):
                continue
            if cleaned_data.get('text'):
                answers.append(cleaned_data)

        if not answers:
            raise ValidationError('Для открытого задания нужно указать минимум один эталонный ответ.')


class MatchingPairForm(forms.Form):
    left_label = forms.CharField(required=False, label='Левая метка')
    left_text = forms.CharField(required=False, label='Левый текст')
    left_sort_order = forms.IntegerField(required=False, label='Левый порядок')

    right_label = forms.CharField(required=False, label='Правая метка')
    right_text = forms.CharField(required=False, label='Правый текст')
    right_sort_order = forms.IntegerField(required=False, label='Правый порядок')


class BaseMatchingPairFormSet(ItemTypeAwareMixin, BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        if self.get_item_type_name() != ITEM_TYPE_MATCHING:
            return

        pairs = []
        for form in self.forms:
            cleaned_data = getattr(form, 'cleaned_data', None)
            if not cleaned_data or cleaned_data.get('DELETE'):
                continue

            row_values = [
                cleaned_data.get('left_label'),
                cleaned_data.get('left_text'),
                cleaned_data.get('left_sort_order'),
                cleaned_data.get('right_label'),
                cleaned_data.get('right_text'),
                cleaned_data.get('right_sort_order'),
            ]

            if any(value not in (None, '') for value in row_values):
                pairs.append(cleaned_data)

        if not pairs:
            raise ValidationError('Для типа "соответствие" нужно указать минимум одну пару.')

        for pair in pairs:
            required_values = [
                pair.get('left_label'),
                pair.get('left_text'),
                pair.get('left_sort_order'),
                pair.get('right_label'),
                pair.get('right_text'),
                pair.get('right_sort_order'),
            ]
            if any(value in (None, '') for value in required_values):
                raise ValidationError('Для соответствия должны быть заполнены все пары полностью.')


AssessmentOptionInlineFormSet = inlineformset_factory(
    AssessmentItem,
    AssessmentOption,
    formset=BaseAssessmentOptionInlineFormSet,
    fields=('text', 'is_correct', 'sort_order'),
    extra=4,
    can_delete=True,
)

AssessmentSequenceInlineFormSet = inlineformset_factory(
    AssessmentItem,
    AssessmentSequenceItem,
    formset=BaseAssessmentSequenceInlineFormSet,
    fields=('text', 'correct_order'),
    extra=4,
    can_delete=True,
)

AssessmentOpenAnswerInlineFormSet = inlineformset_factory(
    AssessmentItem,
    AssessmentOpenAnswer,
    formset=BaseAssessmentOpenAnswerInlineFormSet,
    fields=('text',),
    extra=2,
    can_delete=True,
)

MatchingPairFormSet = formset_factory(
    MatchingPairForm,
    formset=BaseMatchingPairFormSet,
    extra=4,
    can_delete=True,
)