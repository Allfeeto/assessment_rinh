from django.http import JsonResponse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from competencies.models import Competence
from core.models import EducationalProgram
from disciplines.models import Discipline, ProgramDiscipline

from .forms import (
    AssessmentItemForm,
    AssessmentOpenAnswerInlineFormSet,
    AssessmentOptionInlineFormSet,
    AssessmentSequenceInlineFormSet,
    ITEM_TYPE_MATCHING,
    ITEM_TYPE_MULTIPLE,
    ITEM_TYPE_OPEN,
    ITEM_TYPE_SEQUENCE,
    ITEM_TYPE_SINGLE,
    MatchingPairFormSet,
    fetch_assessment_item_competence_ids,
    normalize_item_type_name,
    resolve_item_type_name,
)
from .models import (
    AssessmentItem,
    AssessmentItemType,
    AssessmentMatchAnswer,
    AssessmentMatchLeftItem,
    AssessmentMatchRightItem,
)


def serialize_competences(item_id):
    competence_ids = fetch_assessment_item_competence_ids(item_id)
    competences = Competence.objects.filter(id__in=competence_ids).order_by('code')
    return [
        {
            'id': competence.id,
            'code': competence.code,
            'name': competence.name,
            'type': competence.competence_type.name,
        }
        for competence in competences
    ]


def serialize_assessment_item(item, detailed=False):
    data = {
        'id': item.id,
        'text': item.text,
        'program': {
            'id': item.program_discipline.educational_program_id,
            'code': item.program_discipline.educational_program.code,
            'name': item.program_discipline.educational_program.name,
        },
        'discipline': {
            'id': item.program_discipline.discipline_id,
            'name': item.program_discipline.discipline.name,
        },
        'program_discipline_id': item.program_discipline_id,
        'assessment_item_type': {
            'id': item.assessment_item_type_id,
            'name': item.assessment_item_type.name,
        },
        'competences': serialize_competences(item.id),
    }

    if detailed:
        data['options'] = [
            {
                'id': option.id,
                'text': option.text,
                'is_correct': option.is_correct,
                'sort_order': option.sort_order,
            }
            for option in item.options.order_by('sort_order', 'id')
        ]
        data['matching'] = [
            {
                'left': {
                    'id': left_item.id,
                    'label': left_item.label,
                    'text': left_item.text,
                    'sort_order': left_item.sort_order,
                },
                'right': (
                    {
                        'id': left_item.matched_answer.right_item.id,
                        'label': left_item.matched_answer.right_item.label,
                        'text': left_item.matched_answer.right_item.text,
                        'sort_order': left_item.matched_answer.right_item.sort_order,
                    }
                    if hasattr(left_item, 'matched_answer')
                    else None
                ),
            }
            for left_item in item.matching_left_items.order_by('sort_order', 'id')
        ]
        data['sequence'] = [
            {
                'id': sequence_item.id,
                'text': sequence_item.text,
                'correct_order': sequence_item.correct_order,
            }
            for sequence_item in item.sequence_items.order_by('correct_order', 'id')
        ]
        data['open_answers'] = [
            {
                'id': answer.id,
                'text': answer.text,
            }
            for answer in item.open_answers.order_by('id')
        ]

    return data


def build_assessment_item_queryset(request):
    queryset = (
        AssessmentItem.objects.select_related(
            'program_discipline__educational_program',
            'program_discipline__discipline',
            'assessment_item_type',
        )
        .order_by('id')
    )

    program_id = request.GET.get('program')
    if program_id:
        queryset = queryset.filter(program_discipline__educational_program_id=program_id)

    discipline_id = request.GET.get('discipline')
    if discipline_id:
        queryset = queryset.filter(program_discipline__discipline_id=discipline_id)

    assessment_item_type_id = request.GET.get('assessment_item_type')
    if assessment_item_type_id:
        queryset = queryset.filter(assessment_item_type_id=assessment_item_type_id)

    competence_id = request.GET.get('competence')
    if competence_id:
        queryset = queryset.extra(
            where=[
                'EXISTS (SELECT 1 FROM assessment_item_competence aic '
                'WHERE aic.assessment_item_id = assessment_item.id '
                'AND aic.competence_id = %s)'
            ],
            params=[competence_id],
        )

    return queryset


class AssessmentItemListView(ListView):
    model = AssessmentItem

    def get_queryset(self):
        return build_assessment_item_queryset(self.request)

    def render_to_response(self, context, **response_kwargs):
        items = [serialize_assessment_item(item) for item in context['object_list']]
        return JsonResponse({'results': items, 'count': len(items)})


class AssessmentItemDetailView(DetailView):
    model = AssessmentItem

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                'program_discipline__educational_program',
                'program_discipline__discipline',
                'assessment_item_type',
            )
            .prefetch_related('options', 'matching_left_items', 'sequence_items', 'open_answers')
        )

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse({'result': serialize_assessment_item(context['object'], detailed=True)})


class AssessmentItemPageListView(ListView):
    model = AssessmentItem
    template_name = 'assessment/list.html'
    context_object_name = 'items'
    paginate_by = 12

    def get_queryset(self):
        return build_assessment_item_queryset(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['programs'] = EducationalProgram.objects.order_by('code')
        context['disciplines'] = Discipline.objects.order_by('name')
        context['item_types'] = AssessmentItemType.objects.order_by('name')
        context['selected_program'] = self.request.GET.get('program', '')
        context['selected_discipline'] = self.request.GET.get('discipline', '')
        context['selected_assessment_item_type'] = self.request.GET.get('assessment_item_type', '')
        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_params'] = params.urlencode()
        return context


class AssessmentItemPageDetailView(DetailView):
    model = AssessmentItem
    template_name = 'assessment/detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                'program_discipline__educational_program',
                'program_discipline__discipline',
                'assessment_item_type',
            )
            .prefetch_related(
                'options',
                'matching_left_items',
                'sequence_items',
                'open_answers',
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['competences'] = serialize_competences(self.object.id)
        context['type_name'] = normalize_item_type_name(self.object.assessment_item_type.name)
        context['options'] = self.object.options.order_by('sort_order', 'id')
        context['sequence_items'] = self.object.sequence_items.order_by('correct_order', 'id')
        context['open_answers'] = self.object.open_answers.order_by('id')
        context['matching_pairs'] = [
            {
                'left': left_item,
                'right': left_item.matched_answer.right_item if hasattr(left_item, 'matched_answer') else None,
            }
            for left_item in self.object.matching_left_items.order_by('sort_order', 'id')
        ]
        return context


class AssessmentItemFormsetMixin:
    model = AssessmentItem
    form_class = AssessmentItemForm

    @staticmethod
    def get_metadata():
        return {
            'item_types': list(AssessmentItemType.objects.values('id', 'name').order_by('name')),
            'program_disciplines': list(
                ProgramDiscipline.objects.select_related('educational_program', 'discipline')
                .order_by('educational_program__code', 'discipline__name')
                .values(
                    'id',
                    'discipline__name',
                    'educational_program__code',
                    'educational_program__name',
                )
            ),
        }

    def get_item_type_name(self, form):
        if form.is_bound:
            return resolve_item_type_name(form.data.get('assessment_item_type'))
        if self.object and self.object.assessment_item_type_id:
            return normalize_item_type_name(self.object.assessment_item_type.name)
        return ''

    def get_matching_initial(self):
        if not self.object or not self.object.pk:
            return []

        initial = []
        left_items = self.object.matching_left_items.order_by('sort_order', 'id')
        for left_item in left_items:
            right_item = left_item.matched_answer.right_item if hasattr(left_item, 'matched_answer') else None
            initial.append(
                {
                    'left_label': left_item.label,
                    'left_text': left_item.text,
                    'left_sort_order': left_item.sort_order,
                    'right_label': right_item.label if right_item else '',
                    'right_text': right_item.text if right_item else '',
                    'right_sort_order': right_item.sort_order if right_item else None,
                }
            )
        return initial

    def build_formsets(self, form, data=None):
        instance = self.object if self.object else AssessmentItem()

        option_formset = AssessmentOptionInlineFormSet(
            data=data,
            instance=instance,
            prefix='options',
        )
        sequence_formset = AssessmentSequenceInlineFormSet(
            data=data,
            instance=instance,
            prefix='sequence',
        )
        open_answer_formset = AssessmentOpenAnswerInlineFormSet(
            data=data,
            instance=instance,
            prefix='open',
        )

        if data is None and self.object and self.object.pk:
            matching_formset = MatchingPairFormSet(prefix='matching', initial=self.get_matching_initial())
        else:
            matching_formset = MatchingPairFormSet(data=data, prefix='matching')

        item_type_name = self.get_item_type_name(form)
        option_formset.item_type_name = item_type_name
        sequence_formset.item_type_name = item_type_name
        open_answer_formset.item_type_name = item_type_name
        matching_formset.item_type_name = item_type_name

        return {
            'options': option_formset,
            'matching': matching_formset,
            'sequence': sequence_formset,
            'open_answers': open_answer_formset,
        }

    @staticmethod
    def _collect_formset_errors(formset):
        return {
            'non_form_errors': formset.non_form_errors(),
            'rows': formset.errors,
        }

    def invalid_response(self, form, formsets):
        return JsonResponse(
            {
                'errors': {
                    'form': form.errors,
                    'options': self._collect_formset_errors(formsets['options']),
                    'matching': self._collect_formset_errors(formsets['matching']),
                    'sequence': self._collect_formset_errors(formsets['sequence']),
                    'open_answers': self._collect_formset_errors(formsets['open_answers']),
                }
            },
            status=400,
        )

    @staticmethod
    def _clear_matching_pairs(item):
        AssessmentMatchAnswer.objects.filter(left_item__assessment_item_id=item.id).delete()
        AssessmentMatchLeftItem.objects.filter(assessment_item_id=item.id).delete()
        AssessmentMatchRightItem.objects.filter(assessment_item_id=item.id).delete()

    def _save_matching_pairs(self, item, formset):
        self._clear_matching_pairs(item)

        for row in formset.cleaned_data:
            if not row or row.get('DELETE'):
                continue

            required_values = [
                row.get('left_label'),
                row.get('left_text'),
                row.get('left_sort_order'),
                row.get('right_label'),
                row.get('right_text'),
                row.get('right_sort_order'),
            ]
            if any(value in (None, '') for value in required_values):
                continue

            left_item = AssessmentMatchLeftItem.objects.create(
                assessment_item=item,
                label=row['left_label'],
                text=row['left_text'],
                sort_order=row['left_sort_order'],
            )
            right_item = AssessmentMatchRightItem.objects.create(
                assessment_item=item,
                label=row['right_label'],
                text=row['right_text'],
                sort_order=row['right_sort_order'],
            )
            AssessmentMatchAnswer.objects.create(left_item=left_item, right_item=right_item)

    def save_related_formsets(self, item, formsets):
        item_type_name = normalize_item_type_name(item.assessment_item_type.name)

        option_formset = formsets['options']
        option_formset.instance = item
        if item_type_name in {ITEM_TYPE_SINGLE, ITEM_TYPE_MULTIPLE}:
            option_formset.save()
        else:
            item.options.all().delete()

        sequence_formset = formsets['sequence']
        sequence_formset.instance = item
        if item_type_name == ITEM_TYPE_SEQUENCE:
            sequence_formset.save()
        else:
            item.sequence_items.all().delete()

        open_answer_formset = formsets['open_answers']
        open_answer_formset.instance = item
        if item_type_name == ITEM_TYPE_OPEN:
            open_answer_formset.save()
        else:
            item.open_answers.all().delete()

        if item_type_name == ITEM_TYPE_MATCHING:
            self._save_matching_pairs(item, formsets['matching'])
        else:
            self._clear_matching_pairs(item)


class AssessmentItemCreateView(AssessmentItemFormsetMixin, CreateView):
    model = AssessmentItem
    form_class = AssessmentItemForm

    def get(self, request, *args, **kwargs):
        return JsonResponse(self.get_metadata())

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        formsets = self.build_formsets(form=form, data=request.POST)

        is_valid = form.is_valid() and all(formset.is_valid() for formset in formsets.values())
        if not is_valid:
            return self.invalid_response(form, formsets)

        self.object = form.save()
        self.save_related_formsets(self.object, formsets)
        return JsonResponse({'result': serialize_assessment_item(self.object, detailed=True)}, status=201)


class AssessmentItemUpdateView(AssessmentItemFormsetMixin, UpdateView):
    model = AssessmentItem
    form_class = AssessmentItemForm

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        payload = self.get_metadata()
        payload['result'] = serialize_assessment_item(self.object, detailed=True)
        return JsonResponse(payload)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        formsets = self.build_formsets(form=form, data=request.POST)

        is_valid = form.is_valid() and all(formset.is_valid() for formset in formsets.values())
        if not is_valid:
            return self.invalid_response(form, formsets)

        self.object = form.save()
        self.save_related_formsets(self.object, formsets)
        return JsonResponse({'result': serialize_assessment_item(self.object, detailed=True)})


class AssessmentItemDeleteView(DeleteView):
    model = AssessmentItem

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return JsonResponse({'status': 'deleted'})
