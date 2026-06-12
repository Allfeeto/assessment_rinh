from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView

from assessment.access import program_discipline_queryset_for_user
from assessment.models import AssessmentItem
from competencies.forms import CompetenceIndicatorImportForm
from competencies.models import Competence, CompetenceIndicatorImport, DisciplineCompetence
from core.permissions import get_user_departments, is_domain_manager, is_superuser_or_platform_admin
from core.models import EducationLevel
from core.view_helpers import (
    PER_PAGE_CHOICES,
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
    get_per_page,
    paginate_queryset,
    query_params_without,
)
from disciplines.models import ProgramDiscipline
from teachers.models import Department, TeacherProgramDiscipline

from .forms import EducationalProgramForm, PlxImportUploadForm, ProgramProfileForm, TrainingDirectionForm
from .models import EducationalProgram, ProgramProfile, TrainingDirection
from .services import PlxConflictError, PlxImportError, PlxImportService, PlxProgramUpdateService
from .services.plx_dto import PlxProgramImportDTO
from .services.program_trash_service import ProgramTrashConflictError, ProgramTrashService


class StaffRequiredPostMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        if self.request.method != 'POST':
            return True
        return is_domain_manager(self.request.user)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return is_superuser_or_platform_admin(self.request.user)


def _trash_programs_for_user(user):
    queryset = EducationalProgram.objects.in_trash().select_related(
        'program_profile__training_direction__education_level',
        'department',
        'deleted_by',
    )
    if is_domain_manager(user):
        return queryset

    teacher = getattr(user, 'teacher_profile', None)
    if teacher is None:
        return queryset.none()

    return queryset.filter(
        program_disciplines__teacher_program_disciplines__teacher=teacher
    ).distinct()


class ProgramsDashboardView(LoginRequiredMixin, StaffRequiredPostMixin, TemplateView):
    template_name = 'programs/dashboard.html'
    pending_session_key = 'plx_import_pending_dto'
    import_service = PlxImportService()
    update_service = PlxProgramUpdateService(import_service=import_service)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        per_page = get_per_page(self.request)
        can_manage_programs = is_domain_manager(self.request.user)
        directions_qs = TrainingDirection.objects.select_related('education_level').order_by('code')
        profiles_qs = ProgramProfile.objects.select_related('training_direction').order_by('code')
        programs_qs = EducationalProgram.objects.active().select_related(
            'program_profile__training_direction',
            'department',
        ).order_by('program_profile__code', 'admission_year')
        if not can_manage_programs:
            program_discipline_scope = program_discipline_queryset_for_user(self.request.user)
            directions_qs = directions_qs.filter(
                program_profiles__educational_programs__program_disciplines__in=program_discipline_scope,
            ).distinct()
            profiles_qs = profiles_qs.filter(
                educational_programs__program_disciplines__in=program_discipline_scope,
            ).distinct()
            programs_qs = programs_qs.filter(
                program_disciplines__in=program_discipline_scope,
            ).distinct()

        directions_page_obj = paginate_queryset(
            self.request,
            directions_qs,
            page_param='direction_page',
            per_page=per_page,
        )
        profiles_page_obj = paginate_queryset(
            self.request,
            profiles_qs,
            page_param='profile_page',
            per_page=per_page,
        )
        programs_page_obj = paginate_queryset(
            self.request,
            programs_qs,
            page_param='program_page',
            per_page=per_page,
        )

        context['directions'] = directions_page_obj.object_list
        context['profiles'] = profiles_page_obj.object_list
        context['programs'] = programs_page_obj.object_list
        context['directions_page_obj'] = directions_page_obj
        context['profiles_page_obj'] = profiles_page_obj
        context['programs_page_obj'] = programs_page_obj
        context['directions_query_params'] = query_params_without(self.request, 'direction_page')
        context['profiles_query_params'] = query_params_without(self.request, 'profile_page')
        context['programs_query_params'] = query_params_without(self.request, 'program_page')
        context['per_page_choices'] = PER_PAGE_CHOICES
        context['selected_per_page'] = per_page
        context['can_import_plx'] = can_manage_programs
        context['can_import_indicators'] = can_manage_programs
        context['can_manage_programs'] = is_superuser_or_platform_admin(self.request.user)
        context['import_form'] = kwargs.get('import_form') or PlxImportUploadForm()
        context['import_error'] = kwargs.get('import_error')
        context['import_result'] = kwargs.get('import_result')
        context['import_summary'] = kwargs.get('import_summary')
        context['conflict_program'] = kwargs.get('conflict_program')
        context['pending_conflict'] = kwargs.get('pending_conflict', False)
        context['import_preview'] = kwargs.get('import_preview')
        context['indicator_import_form'] = CompetenceIndicatorImportForm(request_user=self.request.user)
        indicator_imports = CompetenceIndicatorImport.objects.select_related(
            'educational_program__program_profile',
            'educational_program__department',
            'uploaded_by',
        )
        if not is_superuser_or_platform_admin(self.request.user):
            indicator_imports = indicator_imports.filter(
                educational_program__department__in=get_user_departments(self.request.user),
            )
        context['indicator_imports'] = indicator_imports.order_by('-created_at')[:10]
        return context

    def get(self, request, *args, **kwargs):
        pending = self._load_pending_dto(request)
        context_kwargs = {}
        if pending:
            dto, existing_program = pending
            context_kwargs.update(
                {
                    'pending_conflict': True,
                    'import_summary': dto.summary(),
                    'conflict_program': existing_program,
                }
            )
        context = self.get_context_data(**context_kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'upload')
        if action == 'confirm_replace':
            return self._handle_confirm_replace(request)
        if action == 'preview_update':
            return self._handle_preview_update(request)
        if action == 'apply_update':
            return self._handle_apply_update(request)
        if action == 'cancel_replace':
            request.session.pop(self.pending_session_key, None)
            return redirect('programs_root')
        return self._handle_upload(request)

    def _handle_upload(self, request):
        form = PlxImportUploadForm(request.POST, request.FILES)
        context_kwargs = {'import_form': form}
        if not form.is_valid():
            return render(request, self.template_name, self.get_context_data(**context_kwargs), status=400)

        # Шаг 1. Парсинг и маппинг загруженного файла в DTO.
        # Здесь dto ещё не существует, поэтому в обработчиках исключений
        # на dto не ссылаемся (иначе UnboundLocalError при ошибке парсинга).
        try:
            dto = self.import_service.build_dto_from_upload(form.cleaned_data['plx_file'])
        except PlxImportError as exc:
            context_kwargs['import_error'] = str(exc)
            return render(request, self.template_name, self.get_context_data(**context_kwargs), status=400)

        # На этой точке dto гарантированно создан.
        context_kwargs['import_summary'] = dto.summary()

        # Шаг 2. Поиск существующей программы, импорт. Эти ветки уже могут
        # ссылаться на dto, потому что мы дошли сюда без исключения.
        try:
            existing_program = self.import_service.find_existing_program(dto)

            if existing_program:
                request.session[self.pending_session_key] = {
                    'dto': dto.to_dict(),
                    'existing_program_id': existing_program.id,
                }
                context_kwargs['pending_conflict'] = True
                context_kwargs['conflict_program'] = existing_program
                context_kwargs['import_error'] = (
                    'Такая образовательная программа уже существует. '
                    'Выберите отмену, полную замену или безопасное обновление существующей записи.'
                )
                return render(request, self.template_name, self.get_context_data(**context_kwargs), status=409)

            result = self.import_service.import_program(dto, replace_existing=False, user=request.user)
            request.session.pop(self.pending_session_key, None)
            context_kwargs['import_form'] = PlxImportUploadForm()
            context_kwargs['import_result'] = (
                f'Импорт завершен успешно. Создана программа ID={result.created_program_id}. '
                f'Дисциплин: {result.disciplines_count}, '
                f'компетенций: {result.competences_count}, '
                f'связей дисциплина-компетенция: {result.links_count}.'
            )
            return render(request, self.template_name, self.get_context_data(**context_kwargs))
        except PlxConflictError as exc:
            existing_program = None
            if exc.existing_program_id:
                existing_program = EducationalProgram.objects.active().filter(pk=exc.existing_program_id).first()
            request.session[self.pending_session_key] = {
                'dto': dto.to_dict(),
                'existing_program_id': exc.existing_program_id,
            }
            context_kwargs.update(
                {
                    'pending_conflict': True,
                    'conflict_program': existing_program,
                    'import_error': str(exc),
                }
            )
            return render(request, self.template_name, self.get_context_data(**context_kwargs), status=409)
        except PlxImportError as exc:
            context_kwargs['import_error'] = str(exc)
            return render(request, self.template_name, self.get_context_data(**context_kwargs), status=400)

    def _handle_confirm_replace(self, request):
        pending = request.session.get(self.pending_session_key)
        if not pending:
            context = self.get_context_data(
                import_error='Не найдено отложенной операции импорта. Загрузите .plx повторно.',
            )
            return render(request, self.template_name, context, status=400)

        dto = PlxProgramImportDTO.from_dict(pending['dto'])
        context_kwargs = {'import_summary': dto.summary()}
        try:
            result = self.import_service.import_program(dto, replace_existing=True, user=request.user)
            request.session.pop(self.pending_session_key, None)
            replaced_part = (
                f' (старая программа ID={result.replaced_program_id} перемещена в корзину)'
                if result.replaced_program_id
                else ''
            )
            context_kwargs['import_result'] = (
                f'Импорт завершен успешно. Создана программа ID={result.created_program_id}{replaced_part}. '
                f'Дисциплин: {result.disciplines_count}, '
                f'компетенций: {result.competences_count}, '
                f'связей дисциплина-компетенция: {result.links_count}.'
            )
            context_kwargs['import_form'] = PlxImportUploadForm()
            return render(request, self.template_name, self.get_context_data(**context_kwargs))
        except PlxImportError as exc:
            existing_program = None
            existing_program_id = pending.get('existing_program_id')
            if existing_program_id:
                existing_program = EducationalProgram.objects.active().filter(pk=existing_program_id).first()
            context_kwargs.update(
                {
                    'pending_conflict': True,
                    'conflict_program': existing_program,
                    'import_error': str(exc),
                }
            )
            return render(request, self.template_name, self.get_context_data(**context_kwargs), status=400)

    def _handle_preview_update(self, request):
        pending = request.session.get(self.pending_session_key)
        if not pending:
            context = self.get_context_data(
                import_error='Не найдено отложенной операции импорта. Загрузите .plx повторно.',
            )
            return render(request, self.template_name, context, status=400)

        dto = PlxProgramImportDTO.from_dict(pending['dto'])
        existing_program = self._get_pending_existing_program(pending)
        if existing_program is None:
            context = self.get_context_data(
                import_summary=dto.summary(),
                import_error='Существующая программа больше не найдена. Загрузите .plx повторно.',
            )
            return render(request, self.template_name, context, status=400)

        preview = self.update_service.build_preview(dto, existing_program)
        context = self.get_context_data(
            pending_conflict=True,
            import_summary=dto.summary(),
            conflict_program=existing_program,
            import_preview=preview,
        )
        return render(request, self.template_name, context, status=409 if preview.has_blocking_conflicts else 200)

    def _handle_apply_update(self, request):
        pending = request.session.get(self.pending_session_key)
        if not pending:
            context = self.get_context_data(
                import_error='Не найдено отложенной операции импорта. Загрузите .plx повторно.',
            )
            return render(request, self.template_name, context, status=400)

        dto = PlxProgramImportDTO.from_dict(pending['dto'])
        existing_program = self._get_pending_existing_program(pending)
        if existing_program is None:
            context = self.get_context_data(
                import_summary=dto.summary(),
                import_error='Существующая программа больше не найдена. Загрузите .plx повторно.',
            )
            return render(request, self.template_name, context, status=400)

        try:
            result = self.update_service.apply_update(dto, existing_program, user=request.user)
        except PlxImportError as exc:
            preview = self.update_service.build_preview(dto, existing_program)
            context = self.get_context_data(
                pending_conflict=True,
                import_summary=dto.summary(),
                conflict_program=existing_program,
                import_preview=preview,
                import_error=str(exc),
            )
            return render(request, self.template_name, context, status=400)

        request.session.pop(self.pending_session_key, None)
        context = self.get_context_data(
            import_form=PlxImportUploadForm(),
            import_summary=dto.summary(),
            import_result=(
                f'Изменения применены к существующей программе ID={result.program_id}. '
                f'Добавлено дисциплин: {result.created_disciplines}, '
                f'обновлено дисциплин: {result.updated_disciplines}, '
                f'помечено отсутствующими в PLX: {result.marked_inactive_disciplines}, '
                f'добавлено компетенций: {result.created_competences}, '
                f'обновлено компетенций: {result.updated_competences}, '
                f'добавлено связей дисциплина-компетенция: {result.created_links}.'
            ),
        )
        return render(request, self.template_name, context)

    @staticmethod
    def _get_pending_existing_program(pending):
        existing_program_id = pending.get('existing_program_id')
        if not existing_program_id:
            return None
        return (
            EducationalProgram.objects.active()
            .select_related('program_profile__training_direction__education_level', 'department')
            .filter(pk=existing_program_id)
            .first()
        )

    def _load_pending_dto(self, request):
        pending = request.session.get(self.pending_session_key)
        if not pending:
            return None
        dto_data = pending.get('dto')
        if not dto_data:
            return None
        dto = PlxProgramImportDTO.from_dict(dto_data)
        existing_program_id = pending.get('existing_program_id')
        existing_program = None
        if existing_program_id:
            existing_program = self._get_pending_existing_program(pending)
        return dto, existing_program


class TrainingDirectionListView(NamedListView):
    model = TrainingDirection
    title = 'Направления подготовки'
    search_fields = ('code', 'name')
    list_columns = (
        ('ID', 'id'),
        ('Код', 'code'),
        ('Наименование', 'name'),
        ('Уровень', 'education_level.name'),
    )
    create_url_name = 'programs_direction_create'
    detail_url_name = 'programs_direction_detail'
    update_url_name = 'programs_direction_update'
    delete_url_name = 'programs_direction_delete'

    def can_use_action(self, action):
        if action in {'add', 'change', 'delete'}:
            return is_superuser_or_platform_admin(self.request.user)
        return super().can_use_action(action)


class TrainingDirectionDetailView(NamedDetailView):
    model = TrainingDirection
    title = 'Карточка направления'
    list_url_name = 'programs_direction_list'
    update_url_name = 'programs_direction_update'
    delete_url_name = 'programs_direction_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Код', 'code'),
        ('Наименование', 'name'),
        ('Уровень', 'education_level.name'),
    )


class TrainingDirectionCreateView(NamedCreateView):
    model = TrainingDirection
    form_class = TrainingDirectionForm
    title = 'Создать направление'
    list_url_name = 'programs_direction_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)


class TrainingDirectionUpdateView(NamedUpdateView):
    model = TrainingDirection
    form_class = TrainingDirectionForm
    title = 'Редактировать направление'
    list_url_name = 'programs_direction_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)


class TrainingDirectionDeleteView(NamedDeleteView):
    model = TrainingDirection
    title = 'Удалить направление'
    list_url_name = 'programs_direction_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)


class ProgramProfileListView(NamedListView):
    model = ProgramProfile
    title = 'Профили программ'
    search_fields = ('code', 'name', 'training_direction__code')
    list_columns = (
        ('ID', 'id'),
        ('Код профиля', 'code'),
        ('Наименование', 'name'),
        ('Направление', 'training_direction.code'),
    )
    create_url_name = 'programs_profile_create'
    detail_url_name = 'programs_profile_detail'
    update_url_name = 'programs_profile_update'
    delete_url_name = 'programs_profile_delete'

    def can_use_action(self, action):
        if action in {'add', 'change', 'delete'}:
            return is_superuser_or_platform_admin(self.request.user)
        return super().can_use_action(action)


class ProgramProfileDetailView(NamedDetailView):
    model = ProgramProfile
    title = 'Карточка профиля'
    list_url_name = 'programs_profile_list'
    update_url_name = 'programs_profile_update'
    delete_url_name = 'programs_profile_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Код профиля', 'code'),
        ('Наименование', 'name'),
        ('Направление', 'training_direction.code'),
    )


class ProgramProfileCreateView(NamedCreateView):
    model = ProgramProfile
    form_class = ProgramProfileForm
    title = 'Создать профиль'
    list_url_name = 'programs_profile_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)


class ProgramProfileUpdateView(NamedUpdateView):
    model = ProgramProfile
    form_class = ProgramProfileForm
    title = 'Редактировать профиль'
    list_url_name = 'programs_profile_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)


class ProgramProfileDeleteView(NamedDeleteView):
    model = ProgramProfile
    title = 'Удалить профиль'
    list_url_name = 'programs_profile_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)


class EducationalProgramListView(NamedListView):
    model = EducationalProgram
    title = 'Образовательные программы'
    search_fields = (
        'program_profile__code',
        'program_profile__name',
        'department__short_name',
    )
    list_columns = (
        ('ID', 'id'),
        ('Профиль', 'program_profile.code'),
        ('Кафедра', 'department.short_name'),
        ('Год набора', 'admission_year'),
    )
    create_url_name = 'programs_educational_program_create'
    detail_url_name = 'programs_educational_program_detail'
    update_url_name = 'programs_educational_program_update'
    delete_url_name = 'programs_educational_program_delete'

    def can_use_action(self, action):
        if action in {'add', 'change', 'delete'}:
            return is_superuser_or_platform_admin(self.request.user)
        return super().can_use_action(action)

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class EducationalProgramDetailView(NamedDetailView):
    model = EducationalProgram
    title = 'Карточка образовательной программы'
    list_url_name = 'programs_educational_program_list'
    update_url_name = 'programs_educational_program_update'
    delete_url_name = 'programs_educational_program_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Профиль', 'program_profile.code'),
        ('Наименование профиля', 'program_profile.name'),
        ('Направление', 'program_profile.training_direction.code'),
        ('Кафедра', 'department.short_name'),
        ('Год набора', 'admission_year'),
    )

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class EducationalProgramCreateView(NamedCreateView):
    model = EducationalProgram
    form_class = EducationalProgramForm
    title = 'Создать образовательную программу'
    list_url_name = 'programs_educational_program_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)


class EducationalProgramUpdateView(NamedUpdateView):
    model = EducationalProgram
    form_class = EducationalProgramForm
    title = 'Редактировать образовательную программу'
    list_url_name = 'programs_educational_program_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class EducationalProgramDeleteView(NamedDeleteView):
    model = EducationalProgram
    template_name = 'programs/confirm_move_to_trash.html'
    title = 'Переместить образовательную программу в корзину'
    list_url_name = 'programs_educational_program_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        ProgramTrashService().move_to_trash(
            self.object,
            user=request.user,
            reason='Удаление образовательной программы из обычного интерфейса',
        )
        messages.success(
            request,
            'Образовательная программа перемещена в корзину. '
            'Оценочные средства и назначения преподавателей сохранены.',
        )
        return redirect(self.get_success_url())


class ProgramTrashListView(LoginRequiredMixin, TemplateView):
    template_name = 'programs/trash_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        per_page = get_per_page(self.request)

        queryset = _trash_programs_for_user(self.request.user).annotate(
            program_disciplines_count=Count('program_disciplines', distinct=True),
            competences_count=Count('competences', distinct=True),
            assessment_items_count=Count('program_disciplines__assessment_items', distinct=True),
            teacher_assignments_count=Count(
                'program_disciplines__teacher_program_disciplines',
                distinct=True,
            ),
        )
        selected = {
            'education_level': self.request.GET.get('education_level', '').strip(),
            'training_direction': self.request.GET.get('training_direction', '').strip(),
            'program_profile': self.request.GET.get('program_profile', '').strip(),
            'department': self.request.GET.get('department', '').strip(),
            'admission_year': self.request.GET.get('admission_year', '').strip(),
            'q': self.request.GET.get('q', '').strip(),
        }

        if selected['education_level'].isdigit():
            queryset = queryset.filter(
                program_profile__training_direction__education_level_id=selected['education_level']
            )
        if selected['training_direction'].isdigit():
            queryset = queryset.filter(
                program_profile__training_direction_id=selected['training_direction']
            )
        if selected['program_profile'].isdigit():
            queryset = queryset.filter(program_profile_id=selected['program_profile'])
        if selected['department'].isdigit():
            queryset = queryset.filter(department_id=selected['department'])
        if selected['admission_year'].isdigit():
            queryset = queryset.filter(admission_year=selected['admission_year'])
        if selected['q']:
            query = selected['q']
            queryset = queryset.filter(
                Q(program_profile__code__icontains=query)
                | Q(program_profile__name__icontains=query)
                | Q(program_profile__training_direction__code__icontains=query)
                | Q(program_profile__training_direction__name__icontains=query)
                | Q(department__short_name__icontains=query)
                | Q(department__full_name__icontains=query)
            )

        queryset = queryset.order_by('-deleted_at', 'program_profile__code', 'admission_year')
        page_obj = paginate_queryset(self.request, queryset, page_param='page', per_page=per_page)

        context.update(
            {
                'programs': page_obj.object_list,
                'page_obj': page_obj,
                'selected': selected,
                'education_levels': EducationLevel.objects.order_by('name'),
                'training_directions': TrainingDirection.objects.order_by('code'),
                'program_profiles': ProgramProfile.objects.order_by('code'),
                'departments': Department.objects.order_by('number'),
                'per_page_choices': PER_PAGE_CHOICES,
                'selected_per_page': per_page,
                'query_params': query_params_without(self.request, 'page'),
                'can_manage_trash': is_superuser_or_platform_admin(self.request.user),
            }
        )
        return context


class ProgramTrashDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'programs/trash_detail.html'

    def get_program(self):
        return get_object_or_404(
            _trash_programs_for_user(self.request.user),
            pk=self.kwargs['pk'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program = self.get_program()
        program_disciplines = ProgramDiscipline.objects.filter(
            educational_program=program
        ).select_related('discipline', 'department').order_by('discipline_code', 'discipline__name')
        competences = Competence.objects.filter(
            educational_program=program
        ).select_related('competence_type').order_by('code')
        discipline_competences = DisciplineCompetence.objects.filter(
            program_discipline__educational_program=program
        ).select_related(
            'program_discipline__discipline',
            'program_discipline__department',
            'competence__competence_type',
        ).order_by('program_discipline__discipline_code', 'program_discipline__discipline__name', 'competence__code')
        teacher_assignments = TeacherProgramDiscipline.objects.filter(
            program_discipline__educational_program=program
        ).select_related(
            'teacher',
            'program_discipline__discipline',
        ).order_by('teacher__full_name', 'program_discipline__discipline_code', 'program_discipline__discipline__name')

        context.update(
            {
                'program': program,
                'counts': ProgramTrashService().get_counts(program),
                'program_disciplines': program_disciplines,
                'competences': competences,
                'discipline_competences': discipline_competences,
                'teacher_assignments': teacher_assignments,
                'assessment_items_count': AssessmentItem.objects.filter(
                    program_discipline__educational_program=program
                ).count(),
                'can_manage_trash': is_superuser_or_platform_admin(self.request.user),
            }
        )
        return context


class ProgramTrashRestoreView(StaffRequiredMixin, TemplateView):
    template_name = 'programs/confirm_restore.html'

    def get_program(self):
        return get_object_or_404(EducationalProgram.objects.in_trash(), pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program = self.get_program()
        context['program'] = program
        context['counts'] = ProgramTrashService().get_counts(program)
        return context

    def post(self, request, *args, **kwargs):
        program = self.get_program()
        try:
            ProgramTrashService().restore_from_trash(program, user=request.user)
        except ProgramTrashConflictError as exc:
            messages.error(request, str(exc))
            return redirect('programs_trash_detail', pk=program.pk)
        messages.success(
            request,
            'Образовательная программа восстановлена. Дисциплины, компетенции, '
            'оценочные средства и назначения преподавателей снова доступны в обычной рабочей области.',
        )
        return redirect('programs_educational_program_detail', pk=program.pk)


class ProgramTrashHardDeleteView(StaffRequiredMixin, TemplateView):
    template_name = 'programs/confirm_hard_delete.html'

    def get_program(self):
        return get_object_or_404(EducationalProgram.objects.in_trash(), pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program = self.get_program()
        context['program'] = program
        context['counts'] = ProgramTrashService().get_counts(program)
        return context

    def post(self, request, *args, **kwargs):
        program = self.get_program()
        ProgramTrashService().hard_delete(program)
        messages.success(
            request,
            'Образовательная программа и связанные с ней данные окончательно удалены.',
        )
        return redirect('programs_trash')
