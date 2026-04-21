from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from core.view_helpers import (
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
)

from .forms import EducationalProgramForm, PlxImportUploadForm, ProgramProfileForm, TrainingDirectionForm
from .models import EducationalProgram, ProgramProfile, TrainingDirection
from .services import PlxConflictError, PlxImportError, PlxImportService
from .services.plx_dto import PlxProgramImportDTO


class ProgramsDashboardView(TemplateView):
    template_name = 'programs/dashboard.html'
    pending_session_key = 'plx_import_pending_dto'
    import_service = PlxImportService()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['directions'] = TrainingDirection.objects.select_related('education_level').order_by('code')
        context['profiles'] = ProgramProfile.objects.select_related('training_direction').order_by('code')
        context['programs'] = EducationalProgram.objects.select_related(
            'program_profile__training_direction',
            'department',
        ).order_by('program_profile__code', 'admission_year')
        context['import_form'] = kwargs.get('import_form') or PlxImportUploadForm()
        context['import_error'] = kwargs.get('import_error')
        context['import_result'] = kwargs.get('import_result')
        context['import_summary'] = kwargs.get('import_summary')
        context['conflict_program'] = kwargs.get('conflict_program')
        context['pending_conflict'] = kwargs.get('pending_conflict', False)
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
        if action == 'cancel_replace':
            request.session.pop(self.pending_session_key, None)
            return redirect('programs_root')
        return self._handle_upload(request)

    def _handle_upload(self, request):
        form = PlxImportUploadForm(request.POST, request.FILES)
        context_kwargs = {'import_form': form}
        if not form.is_valid():
            return render(request, self.template_name, self.get_context_data(**context_kwargs), status=400)

        try:
            dto = self.import_service.build_dto_from_upload(form.cleaned_data['plx_file'])
            existing_program = self.import_service.find_existing_program(dto)
            context_kwargs['import_summary'] = dto.summary()

            if existing_program:
                request.session[self.pending_session_key] = {
                    'dto': dto.to_dict(),
                    'existing_program_id': existing_program.id,
                }
                context_kwargs['pending_conflict'] = True
                context_kwargs['conflict_program'] = existing_program
                context_kwargs['import_error'] = (
                    'Такая образовательная программа уже существует. '
                    'Подтвердите замену для полного обновления данных.'
                )
                return render(request, self.template_name, self.get_context_data(**context_kwargs), status=409)

            result = self.import_service.import_program(dto, replace_existing=False)
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
                existing_program = EducationalProgram.objects.filter(pk=exc.existing_program_id).first()
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
            result = self.import_service.import_program(dto, replace_existing=True)
            request.session.pop(self.pending_session_key, None)
            replaced_part = (
                f' (заменена программа ID={result.replaced_program_id})'
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
                existing_program = EducationalProgram.objects.filter(pk=existing_program_id).first()
            context_kwargs.update(
                {
                    'pending_conflict': True,
                    'conflict_program': existing_program,
                    'import_error': str(exc),
                }
            )
            return render(request, self.template_name, self.get_context_data(**context_kwargs), status=400)

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
            existing_program = EducationalProgram.objects.filter(pk=existing_program_id).first()
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


class TrainingDirectionUpdateView(NamedUpdateView):
    model = TrainingDirection
    form_class = TrainingDirectionForm
    title = 'Редактировать направление'
    list_url_name = 'programs_direction_list'


class TrainingDirectionDeleteView(NamedDeleteView):
    model = TrainingDirection
    title = 'Удалить направление'
    list_url_name = 'programs_direction_list'


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


class ProgramProfileUpdateView(NamedUpdateView):
    model = ProgramProfile
    form_class = ProgramProfileForm
    title = 'Редактировать профиль'
    list_url_name = 'programs_profile_list'


class ProgramProfileDeleteView(NamedDeleteView):
    model = ProgramProfile
    title = 'Удалить профиль'
    list_url_name = 'programs_profile_list'


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


class EducationalProgramCreateView(NamedCreateView):
    model = EducationalProgram
    form_class = EducationalProgramForm
    title = 'Создать образовательную программу'
    list_url_name = 'programs_educational_program_list'


class EducationalProgramUpdateView(NamedUpdateView):
    model = EducationalProgram
    form_class = EducationalProgramForm
    title = 'Редактировать образовательную программу'
    list_url_name = 'programs_educational_program_list'


class EducationalProgramDeleteView(NamedDeleteView):
    model = EducationalProgram
    title = 'Удалить образовательную программу'
    list_url_name = 'programs_educational_program_list'


def profiles_by_direction(request):
    direction_id = request.GET.get('direction_id')
    queryset = ProgramProfile.objects.order_by('code')
    if direction_id:
        queryset = queryset.filter(training_direction_id=direction_id)

    data = [{'id': profile.id, 'label': str(profile)} for profile in queryset]
    return JsonResponse({'results': data})
