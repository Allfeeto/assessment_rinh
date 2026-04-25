from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import DeleteView, DetailView, ListView, TemplateView

from competencies.models import Competence
from core.models import AssessmentItemType, EducationLevel
from core.view_helpers import PER_PAGE_CHOICES, get_per_page, paginate_queryset
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection

from .access import allowed_program_discipline_ids_for_user as _allowed_program_discipline_ids_for_user
from .forms import AssessmentItemForm, AssessmentItemRowCreateFormSet, AssessmentItemRowUpdateFormSet
from .models import AssessmentItem
from .services import (
    clone_assessment_item_to_program_discipline,
    get_clipboard_item_ids,
    get_item_competence_codes,
    get_item_competences,
    get_item_type_ui_name,
    get_ui_assessment_item_types_queryset,
    infer_item_type_code,
    prettify_db_error,
    set_clipboard_item_ids,
    split_rows_for_detail,
    sync_assessment_item_competences,
)


def _safe_next_url(request, fallback):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback


def _restrict_queryset_for_teacher_user(request, queryset):
    user = request.user
    if not user.is_authenticated:
        return queryset.none()

    if user.is_superuser:
        return queryset

    teacher = getattr(user, 'teacher_profile', None)
    if not teacher:
        return queryset.none()

    allowed_ids = _allowed_program_discipline_ids_for_user(user)
    return queryset.filter(program_discipline_id__in=allowed_ids)


class AssessmentItemListView(LoginRequiredMixin, ListView):
    model = AssessmentItem
    template_name = 'assessment/list.html'
    context_object_name = 'items'
    paginate_by = 50
    per_page_choices = (50, 100, 200)
    login_url = reverse_lazy('login')

    def get_paginate_by(self, queryset):
        raw_value = (self.request.GET.get('per_page') or '').strip()
        if raw_value.isdigit():
            per_page = int(raw_value)
            if per_page in self.per_page_choices:
                return per_page
        return self.paginate_by

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
            .prefetch_related('competence_links__competence')
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
            queryset = queryset.filter(
                Q(competence_id=competence_id) | Q(competence_links__competence_id=competence_id)
            ).distinct()

        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(prompt_text__icontains=search_query)

        return _restrict_queryset_for_teacher_user(self.request, queryset)

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
            'per_page': self.request.GET.get('per_page', str(self.paginate_by)),
        }
        context['per_page_choices'] = self.per_page_choices

        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_params'] = params.urlencode()

        for item in context['items']:
            item.ui_competence_codes = get_item_competence_codes(item)
        return context


class AssessmentItemDetailView(LoginRequiredMixin, DetailView):
    model = AssessmentItem
    template_name = 'assessment/detail.html'
    context_object_name = 'item'
    login_url = reverse_lazy('login')

    def get_queryset(self):
        queryset = (
            AssessmentItem.objects.select_related(
                'program_discipline__discipline',
                'program_discipline__educational_program__program_profile__training_direction',
                'assessment_item_type',
                'competence__competence_type',
            )
            .prefetch_related('rows', 'competence_links__competence')
            .order_by('-id')
        )
        return _restrict_queryset_for_teacher_user(self.request, queryset)

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
        context['item_competences'] = get_item_competences(self.object)
        context['back_url'] = _safe_next_url(self.request, reverse('assessment_list'))
        return context


class AssessmentItemFormMixin:
    template_name = 'assessment/form.html'
    model = AssessmentItem
    form_class = AssessmentItemForm
    row_formset_class = AssessmentItemRowCreateFormSet

    def get_success_url(self):
        return _safe_next_url(self.request, reverse('assessment_list'))

    @staticmethod
    def _resolve_item_type_name(form, obj):
        if form.is_bound:
            item_type_id = form.data.get('assessment_item_type')
            if item_type_id:
                item_type = AssessmentItemType.objects.filter(pk=item_type_id).first()
                if item_type:
                    return item_type.name
            return ''

        if obj and obj.assessment_item_type_id:
            return obj.assessment_item_type.name

        return ''

    def _get_initial(self):
        initial = {}
        program_discipline_id = self.request.GET.get('program_discipline')
        if program_discipline_id:
            initial['program_discipline'] = program_discipline_id

        competence_id = self.request.GET.get('competence')
        if competence_id and competence_id.isdigit():
            initial['competencies'] = [int(competence_id)]
        return initial

    def _get_formset(self, data=None):
        instance = self.object if getattr(self, 'object', None) else AssessmentItem()
        return self.row_formset_class(data=data, instance=instance, prefix='rows')

    def _save_item_and_formset(self, form, formset):
        selected_competences = list(form.cleaned_data.get('competencies') or [])
        if not selected_competences:
            raise ValueError('Выберите хотя бы одну компетенцию для задания.')

        item = form.save(commit=False)
        # При смене дисциплины учебного плана обнуляем основную компетенцию до синхронизации.
        item.competence = None
        item.save()
        sync_assessment_item_competences(item, selected_competences)

        formset.instance = item
        formset.save()
        self.object = item

    def _validate_teacher_scope(self, form):
        user = self.request.user
        if not user.is_authenticated or user.is_superuser:
            return True

        teacher = getattr(user, 'teacher_profile', None)
        if not teacher:
            form.add_error(
                None,
                'Для вашего пользователя не создан профиль преподавателя. '
                'Обратитесь к администратору.',
            )
            return False

        allowed_ids = set(_allowed_program_discipline_ids_for_user(user))
        selected_program_discipline = form.cleaned_data.get('program_discipline')
        if not selected_program_discipline or selected_program_discipline.id not in allowed_ids:
            form.add_error(
                'program_discipline',
                'У вас нет доступа к выбранной дисциплине учебного плана.',
            )
            return False
        return True

    def _render(self, request, form, formset, title):
        item_type_name = self._resolve_item_type_name(form, getattr(self, 'object', None))
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
                'next_url': _safe_next_url(request, reverse('assessment_list')),
            },
        )


class AssessmentItemCreateView(LoginRequiredMixin, AssessmentItemFormMixin, View):
    row_formset_class = AssessmentItemRowCreateFormSet
    login_url = reverse_lazy('login')

    def get(self, request, *args, **kwargs):
        self.object = None
        form = self.form_class(initial=self._get_initial())
        formset = self._get_formset()
        formset.item_type_name = self._resolve_item_type_name(form, None)
        return self._render(request, form, formset, 'Создать задание')

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.form_class(request.POST)
        formset = self._get_formset(data=request.POST)
        formset.item_type_name = self._resolve_item_type_name(form, None)

        form_valid = form.is_valid()
        formset_valid = formset.is_valid()
        scope_valid = self._validate_teacher_scope(form) if form_valid else False

        if form_valid and formset_valid and scope_valid:
            try:
                with transaction.atomic():
                    self._save_item_and_formset(form, formset)
                return redirect(self.get_success_url())
            except (DatabaseError, ValueError) as exc:
                form.add_error(None, prettify_db_error(exc))

        return self._render(request, form, formset, 'Создать задание')


class AssessmentItemUpdateView(LoginRequiredMixin, AssessmentItemFormMixin, View):
    row_formset_class = AssessmentItemRowUpdateFormSet
    login_url = reverse_lazy('login')

    def get_object(self):
        queryset = _restrict_queryset_for_teacher_user(self.request, AssessmentItem.objects.all())
        return get_object_or_404(queryset, pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.form_class(instance=self.object)
        formset = self._get_formset()
        formset.item_type_name = self._resolve_item_type_name(form, self.object)
        return self._render(request, form, formset, 'Редактировать задание')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.form_class(request.POST, instance=self.object)
        formset = self._get_formset(data=request.POST)
        formset.item_type_name = self._resolve_item_type_name(form, self.object)

        form_valid = form.is_valid()
        formset_valid = formset.is_valid()
        scope_valid = self._validate_teacher_scope(form) if form_valid else False

        if form_valid and formset_valid and scope_valid:
            try:
                with transaction.atomic():
                    self._save_item_and_formset(form, formset)
                return redirect(self.get_success_url())
            except (DatabaseError, ValueError) as exc:
                form.add_error(None, prettify_db_error(exc))

        return self._render(request, form, formset, 'Редактировать задание')


class AssessmentItemDeleteView(LoginRequiredMixin, DeleteView):
    model = AssessmentItem
    template_name = 'common/confirm_delete.html'
    login_url = reverse_lazy('login')

    def get_queryset(self):
        queryset = AssessmentItem.objects.all()
        return _restrict_queryset_for_teacher_user(self.request, queryset)

    def get_success_url(self):
        return _safe_next_url(self.request, reverse('assessment_list'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удалить задание'
        context['list_url_name'] = 'assessment_list'
        return context


class TeacherRequiredMixin(LoginRequiredMixin):
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        teacher = getattr(request.user, 'teacher_profile', None)
        if teacher is None:
            messages.error(
                request,
                'Для вашего пользователя не создан профиль преподавателя. '
                'Обратитесь к администратору.',
            )
            return redirect('home')

        self.teacher = teacher
        return super().dispatch(request, *args, **kwargs)


class TeacherWorkspaceView(TeacherRequiredMixin, TemplateView):
    template_name = 'assessment/workspace.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if hasattr(self, 'teacher'):
            available_program_disciplines_all = list(
                ProgramDiscipline.objects.filter(
                    teacher_program_disciplines__teacher=self.teacher
                )
                .select_related(
                    'educational_program__program_profile__training_direction',
                    'educational_program__department',
                    'discipline',
                )
                .distinct()
            )
        else:
            available_program_disciplines_all = list(
                ProgramDiscipline.objects.select_related(
                    'educational_program__program_profile__training_direction',
                    'educational_program__department',
                    'discipline',
                )
            )

        program_map = {}
        for program_discipline in available_program_disciplines_all:
            program = program_discipline.educational_program
            program_map[program.id] = program
        programs = sorted(
            program_map.values(),
            key=lambda program: (program.program_profile.code, program.admission_year, program.id),
        )

        selected_program_id = self.request.GET.get('program')
        if selected_program_id and not selected_program_id.isdigit():
            selected_program_id = ''
        if not selected_program_id and programs:
            selected_program_id = str(programs[0].id)

        available_program_disciplines = [
            program_discipline
            for program_discipline in available_program_disciplines_all
            if not selected_program_id or str(program_discipline.educational_program_id) == selected_program_id
        ]
        available_program_disciplines.sort(key=lambda pd: pd.discipline.name.lower())

        selected_program_discipline_id = self.request.GET.get('program_discipline')
        valid_program_discipline_ids = {str(pd.id) for pd in available_program_disciplines}
        if selected_program_discipline_id not in valid_program_discipline_ids:
            selected_program_discipline_id = ''
        if not selected_program_discipline_id and available_program_disciplines:
            selected_program_discipline_id = str(available_program_disciplines[0].id)

        current_program_discipline = next(
            (
                program_discipline
                for program_discipline in available_program_disciplines
                if str(program_discipline.id) == selected_program_discipline_id
            ),
            None,
        )

        selected_competence = self.request.GET.get('competence', '')
        selected_item_type = self.request.GET.get('assessment_item_type', '')
        if selected_competence and not selected_competence.isdigit():
            selected_competence = ''
        if selected_item_type and not selected_item_type.isdigit():
            selected_item_type = ''
        per_page = get_per_page(self.request)

        competences = Competence.objects.none()
        items = AssessmentItem.objects.none()
        if current_program_discipline:
            competences = (
                Competence.objects.select_related('competence_type')
                .filter(
                    discipline_competences__program_discipline=current_program_discipline
                )
                .distinct()
                .order_by('code')
            )
            if selected_competence and not competences.filter(pk=selected_competence).exists():
                selected_competence = ''

            items = (
                AssessmentItem.objects.filter(program_discipline=current_program_discipline)
                .select_related(
                    'assessment_item_type',
                    'competence',
                    'program_discipline__discipline',
                    'program_discipline__educational_program__program_profile',
                )
                .prefetch_related('competence_links__competence')
                .order_by('-id')
            )
            if selected_competence:
                items = items.filter(
                    Q(competence_id=selected_competence) | Q(competence_links__competence_id=selected_competence)
                ).distinct()
            if selected_item_type:
                items = items.filter(assessment_item_type_id=selected_item_type)

        items_page_obj = paginate_queryset(
            self.request,
            items,
            page_param='page',
            per_page=per_page,
        )
        items_page = list(items_page_obj.object_list)

        assessment_item_types = list(get_ui_assessment_item_types_queryset())
        for item_type in assessment_item_types:
            item_type.ui_name = get_item_type_ui_name(item_type.name)

        for item in items_page:
            item.ui_competence_codes = get_item_competence_codes(item)

        item_query_params = self.request.GET.copy()
        item_query_params.pop('page', None)
        normalized_params = {
            'program': selected_program_id,
            'program_discipline': selected_program_discipline_id,
            'competence': selected_competence,
            'assessment_item_type': selected_item_type,
            'per_page': str(per_page),
        }
        for key, value in normalized_params.items():
            if value:
                item_query_params[key] = value
            else:
                item_query_params.pop(key, None)

        next_params = item_query_params.copy()
        if items_page_obj.number > 1:
            next_params['page'] = str(items_page_obj.number)
        next_url = self.request.path
        if next_params:
            next_url = f'{next_url}?{next_params.urlencode()}'

        context.update(
            {
                'teacher': getattr(self, 'teacher', None),
                'programs': programs,
                'available_program_disciplines': available_program_disciplines,
                'current_program_discipline': current_program_discipline,
                'selected_program': selected_program_id,
                'selected_program_discipline': selected_program_discipline_id,
                'selected_competence': selected_competence,
                'selected_item_type': selected_item_type,
                'competences': competences,
                'assessment_item_types': assessment_item_types,
                'items': items_page,
                'items_page_obj': items_page_obj,
                'items_query_params': item_query_params.urlencode(),
                'per_page_choices': PER_PAGE_CHOICES,
                'selected_per_page': per_page,
                'clipboard_count': len(get_clipboard_item_ids(self.request.session)),
                'next_url': next_url,
            }
        )
        return context


class TeacherWorkspaceCopyItemsView(TeacherRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        next_url = _safe_next_url(request, reverse('assessment_workspace'))
        item_ids = request.POST.getlist('item_ids')
        single_item_id = request.POST.get('item_id')
        if single_item_id:
            item_ids.append(single_item_id)

        allowed_program_discipline_ids = _allowed_program_discipline_ids_for_user(request.user)
        valid_item_ids = list(
            AssessmentItem.objects.filter(
                id__in=item_ids,
                program_discipline_id__in=allowed_program_discipline_ids,
            ).values_list('id', flat=True)
        )

        if not valid_item_ids:
            messages.error(request, 'Не удалось скопировать задания: выберите минимум одно доступное задание.')
            return redirect(next_url)

        set_clipboard_item_ids(request.session, valid_item_ids)
        messages.success(request, f'Скопировано заданий: {len(valid_item_ids)}.')
        return redirect(next_url)


class TeacherWorkspacePasteItemsView(TeacherRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        next_url = _safe_next_url(request, reverse('assessment_workspace'))
        clipboard_item_ids = get_clipboard_item_ids(request.session)
        if not clipboard_item_ids:
            messages.error(request, 'Буфер копирования пуст. Сначала скопируйте одно или несколько заданий.')
            return redirect(next_url)

        target_program_discipline_id = request.POST.get('program_discipline')
        if not target_program_discipline_id or not target_program_discipline_id.isdigit():
            messages.error(request, 'Не выбрана целевая дисциплина учебного плана для вставки.')
            return redirect(next_url)

        allowed_program_discipline_ids = _allowed_program_discipline_ids_for_user(request.user)
        if int(target_program_discipline_id) not in allowed_program_discipline_ids:
            messages.error(request, 'У вас нет доступа к выбранной дисциплине учебного плана.')
            return redirect(next_url)

        target_program_discipline = get_object_or_404(
            ProgramDiscipline.objects.select_related('educational_program', 'discipline'),
            pk=target_program_discipline_id,
        )

        source_items = list(
            AssessmentItem.objects.filter(
                id__in=clipboard_item_ids,
                program_discipline_id__in=allowed_program_discipline_ids,
            )
            .select_related('assessment_item_type', 'program_discipline', 'competence')
            .prefetch_related('rows', 'competence_links__competence')
            .order_by('id')
        )
        if not source_items:
            messages.error(request, 'В буфере нет доступных заданий для вставки.')
            return redirect(next_url)
        if len(source_items) < len(set(clipboard_item_ids)):
            messages.warning(
                request,
                'Часть заданий из буфера больше недоступна и не будет вставлена.',
            )

        copied_count = 0
        no_competence_count = 0
        try:
            with transaction.atomic():
                for source_item in source_items:
                    _, transferred_competences = clone_assessment_item_to_program_discipline(
                        source_item,
                        target_program_discipline,
                    )
                    copied_count += 1
                    if not transferred_competences:
                        no_competence_count += 1
        except DatabaseError as exc:
            messages.error(request, prettify_db_error(exc))
            return redirect(next_url)

        if no_competence_count:
            messages.warning(
                request,
                (
                    f'Вставлено заданий: {copied_count}. '
                    f'Для {no_competence_count} заданий компетенции не перенесены '
                    'из-за несовместимого контекста — назначьте их вручную.'
                ),
            )
        else:
            messages.success(request, f'Успешно вставлено заданий: {copied_count}.')
        return redirect(next_url)


class TeacherWorkspaceClearClipboardView(TeacherRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        next_url = _safe_next_url(request, reverse('assessment_workspace'))
        set_clipboard_item_ids(request.session, [])
        messages.success(request, 'Буфер копирования очищен.')
        return redirect(next_url)
