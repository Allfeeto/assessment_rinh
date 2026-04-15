from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView, DetailView, ListView

from competencies.models import Competence
from core.models import AssessmentItemType, EducationLevel
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection

from .forms import AssessmentItemForm, AssessmentItemRowCreateFormSet, AssessmentItemRowUpdateFormSet
from .models import AssessmentItem
from .services import (
    get_item_type_ui_name,
    get_ui_assessment_item_types_queryset,
    infer_item_type_code,
    prettify_db_error,
    split_rows_for_detail,
)


class AssessmentItemListView(ListView):
    model = AssessmentItem
    template_name = 'assessment/list.html'
    context_object_name = 'items'
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            AssessmentItem.objects.select_related(
                'program_discipline__discipline',
                'program_discipline__educational_program__program_profile__training_direction__education_level',
                'program_discipline__educational_program__program_profile__training_direction',
                'program_discipline__educational_program__program_profile',
                'program_discipline__educational_program',
                'assessment_item_type',
                'competence__competence_type',
            )
            .order_by('-id')
        )

        education_level_id = self.request.GET.get('education_level')
        if education_level_id:
            queryset = queryset.filter(
                program_discipline__educational_program__program_profile__training_direction__education_level_id=education_level_id
            )

        training_direction_id = self.request.GET.get('training_direction')
        if training_direction_id:
            queryset = queryset.filter(
                program_discipline__educational_program__program_profile__training_direction_id=training_direction_id
            )

        program_profile_id = self.request.GET.get('program_profile')
        if program_profile_id:
            queryset = queryset.filter(
                program_discipline__educational_program__program_profile_id=program_profile_id
            )

        educational_program_id = self.request.GET.get('educational_program')
        if educational_program_id:
            queryset = queryset.filter(program_discipline__educational_program_id=educational_program_id)

        discipline_id = self.request.GET.get('discipline')
        if discipline_id:
            queryset = queryset.filter(program_discipline__discipline_id=discipline_id)

        assessment_item_type_id = self.request.GET.get('assessment_item_type')
        if assessment_item_type_id:
            queryset = queryset.filter(assessment_item_type_id=assessment_item_type_id)

        competence_id = self.request.GET.get('competence')
        if competence_id:
            queryset = queryset.filter(competence_id=competence_id)

        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(prompt_text__icontains=search_query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        selected_education_level = self.request.GET.get('education_level', '')
        selected_training_direction = self.request.GET.get('training_direction', '')
        selected_program_profile = self.request.GET.get('program_profile', '')
        selected_educational_program = self.request.GET.get('educational_program', '')
        selected_discipline = self.request.GET.get('discipline', '')

        directions = TrainingDirection.objects.order_by('code')
        profiles = ProgramProfile.objects.order_by('code')
        programs = EducationalProgram.objects.select_related('program_profile', 'department').order_by(
            'program_profile__code',
            'admission_year',
        )
        competences = Competence.objects.select_related('competence_type').order_by('code')

        if selected_education_level:
            directions = directions.filter(education_level_id=selected_education_level)
            profiles = profiles.filter(training_direction__education_level_id=selected_education_level)
            programs = programs.filter(
                program_profile__training_direction__education_level_id=selected_education_level
            )
            competences = competences.filter(
                educational_program__program_profile__training_direction__education_level_id=selected_education_level
            )

        if selected_training_direction:
            profiles = profiles.filter(training_direction_id=selected_training_direction)
            programs = programs.filter(program_profile__training_direction_id=selected_training_direction)
            competences = competences.filter(
                educational_program__program_profile__training_direction_id=selected_training_direction
            )

        if selected_program_profile:
            programs = programs.filter(program_profile_id=selected_program_profile)
            competences = competences.filter(educational_program__program_profile_id=selected_program_profile)

        if selected_educational_program:
            competences = competences.filter(educational_program_id=selected_educational_program)

        if selected_discipline and selected_educational_program:
            program_discipline_ids = ProgramDiscipline.objects.filter(
                educational_program_id=selected_educational_program,
                discipline_id=selected_discipline,
            ).values_list('id', flat=True)
            competences = competences.filter(
                discipline_competences__program_discipline_id__in=program_discipline_ids
            ).distinct()

        context['education_levels'] = EducationLevel.objects.order_by('id')
        context['training_directions'] = directions
        context['program_profiles'] = profiles
        context['educational_programs'] = programs
        context['disciplines'] = Discipline.objects.order_by('name')
        assessment_item_types = list(get_ui_assessment_item_types_queryset())
        for item_type in assessment_item_types:
            item_type.ui_name = get_item_type_ui_name(item_type.name)
        context['assessment_item_types'] = assessment_item_types
        context['competences'] = competences

        context['selected'] = {
            'education_level': selected_education_level,
            'training_direction': selected_training_direction,
            'program_profile': selected_program_profile,
            'educational_program': selected_educational_program,
            'discipline': selected_discipline,
            'assessment_item_type': self.request.GET.get('assessment_item_type', ''),
            'competence': self.request.GET.get('competence', ''),
            'q': self.request.GET.get('q', ''),
        }

        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_params'] = params.urlencode()
        return context


class AssessmentItemDetailView(DetailView):
    model = AssessmentItem
    template_name = 'assessment/detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        return (
            AssessmentItem.objects.select_related(
                'program_discipline__discipline',
                'program_discipline__educational_program__program_profile__training_direction',
                'assessment_item_type',
                'competence__competence_type',
            )
            .prefetch_related('rows')
            .order_by('-id')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        rows = list(self.object.rows.order_by('sort_order', 'id'))
        split = split_rows_for_detail(self.object.assessment_item_type.name, rows)

        context['rows'] = rows
        context['item_type_code'] = split['code']
        context['item_type_ui_name'] = get_item_type_ui_name(self.object.assessment_item_type.name)
        context['options'] = split['options']
        context['matching_pairs'] = split['matching_pairs']
        context['matching_distractors'] = split['matching_distractors']
        context['sequence_items'] = split['sequence_items']
        context['open_answers'] = split['open_answers']
        return context


class AssessmentItemFormMixin:
    template_name = 'assessment/form.html'
    model = AssessmentItem
    form_class = AssessmentItemForm
    row_formset_class = AssessmentItemRowCreateFormSet

    def get_success_url(self):
        return reverse_lazy('assessment_list')

    def _resolve_item_type_name(self, form):
        if form.is_bound:
            item_type_id = form.data.get('assessment_item_type')
            if item_type_id:
                item_type = AssessmentItemType.objects.filter(pk=item_type_id).first()
                if item_type:
                    return item_type.name
            return ''

        if self.object and self.object.assessment_item_type_id:
            return self.object.assessment_item_type.name

        return ''

    def _get_formset(self, data=None):
        instance = self.object if getattr(self, 'object', None) else AssessmentItem()
        return self.row_formset_class(data=data, instance=instance, prefix='rows')

    def _render(self, request, form, formset, title):
        item_type_name = self._resolve_item_type_name(form)
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'formset': formset,
                'title': title,
                'item_type_name': item_type_name,
                'item_type_code': infer_item_type_code(item_type_name),
                'item_type_ui_name': get_item_type_ui_name(item_type_name),
            },
        )


class AssessmentItemCreateView(AssessmentItemFormMixin, View):
    row_formset_class = AssessmentItemRowCreateFormSet

    def get(self, request, *args, **kwargs):
        self.object = None
        form = self.form_class()
        formset = self._get_formset()
        formset.item_type_name = self._resolve_item_type_name(form)
        return self._render(request, form, formset, 'Создать задание')

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.form_class(request.POST)
        formset = self._get_formset(data=request.POST)
        formset.item_type_name = self._resolve_item_type_name(form)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    self.object = form.save()
                    formset.instance = self.object
                    formset.save()
                return redirect(self.get_success_url())
            except DatabaseError as exc:
                form.add_error(None, prettify_db_error(exc))

        return self._render(request, form, formset, 'Создать задание')


class AssessmentItemUpdateView(AssessmentItemFormMixin, View):
    row_formset_class = AssessmentItemRowUpdateFormSet

    def get_object(self):
        return get_object_or_404(AssessmentItem, pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.form_class(instance=self.object)
        formset = self._get_formset()
        formset.item_type_name = self._resolve_item_type_name(form)
        return self._render(request, form, formset, 'Редактировать задание')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.form_class(request.POST, instance=self.object)
        formset = self._get_formset(data=request.POST)
        formset.item_type_name = self._resolve_item_type_name(form)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    self.object = form.save()
                    formset.instance = self.object
                    formset.save()
                return redirect(self.get_success_url())
            except DatabaseError as exc:
                form.add_error(None, prettify_db_error(exc))

        return self._render(request, form, formset, 'Редактировать задание')


class AssessmentItemDeleteView(DeleteView):
    model = AssessmentItem
    template_name = 'common/confirm_delete.html'
    success_url = reverse_lazy('assessment_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удалить задание'
        context['list_url_name'] = 'assessment_list'
        return context
