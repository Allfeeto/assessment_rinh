import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from assessment.access import allowed_program_discipline_ids_for_user
from core.permissions import (
    assignment_denial_reason,
    can_assign_teacher_to_program_discipline,
    can_manage_teacher,
    can_manage_teacher_assignments,
    filter_program_disciplines_for_assignment,
    filter_teachers_for_assignment,
    get_assignment_availability,
    get_user_departments,
    is_senior_teacher,
    is_staff_or_superuser,
    is_superuser_or_platform_admin,
)
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
from programs.models import EducationalProgram

from .forms import DepartmentForm, TeacherForm, TeacherProgramDisciplineForm
from .models import Department, Teacher, TeacherProgramDiscipline


def _resolve_active_teacher(request):
    """
    Кто сейчас «активный преподаватель» в панели назначений.
    - Обычный преподаватель — это всегда он сам.
    - Администратор/staff может выбрать любого через ?teacher=ID.
    Возвращает (teacher, can_change_teacher).
    """
    user = request.user
    profile = getattr(user, 'teacher_profile', None)
    can_change = can_manage_teacher_assignments(user)

    requested_id = request.GET.get('teacher') or request.POST.get('teacher')
    available_teachers = Teacher.objects.all()
    if can_change:
        available_teachers = filter_teachers_for_assignment(user, available_teachers)

    if can_change and requested_id and str(requested_id).isdigit():
        teacher = available_teachers.filter(pk=int(requested_id)).first()
        if teacher is not None:
            return teacher, True

    if profile is not None:
        return profile, can_change

    if can_change:
        teacher = available_teachers.order_by('full_name').first()
        return teacher, True

    return None, False


def _user_can_assign(user, teacher):
    """Может ли пользователь назначать/снимать активного преподавателя."""
    if not user.is_authenticated or teacher is None:
        return False
    if is_superuser_or_platform_admin(user):
        return True
    if can_manage_teacher_assignments(user) and is_senior_teacher(user):
        return can_manage_teacher(user, teacher)
    return can_manage_teacher_assignments(user)


def _assignment_program_discipline_ids_for_user(user):
    if can_manage_teacher_assignments(user):
        return None
    return set(allowed_program_discipline_ids_for_user(user))


def _program_is_visible_for_assignments(user, program_id):
    if not program_id:
        return False
    if can_manage_teacher_assignments(user):
        return EducationalProgram.objects.filter(pk=program_id, is_deleted=False).exists()

    visible_ids = _assignment_program_discipline_ids_for_user(user)
    if not visible_ids:
        return False
    return ProgramDiscipline.objects.filter(
        pk__in=visible_ids,
        educational_program_id=program_id,
        educational_program__is_deleted=False,
    ).exists()


def _build_assignment_rows(teacher, educational_program, query, user):
    """
    Список ProgramDiscipline для активного преподавателя и выбранной программы.
    Возвращает список словарей: id, discipline_name, is_assigned (для активного teacher),
    other_teachers (строка с ФИО других назначенных).
    Сортировка: сначала уже назначенные, затем доступные для назначения,
    затем прежний порядок по коду и названию дисциплины.
    """
    if educational_program is None:
        return []

    program_disciplines = (
        ProgramDiscipline.objects.filter(
            educational_program=educational_program,
            educational_program__is_deleted=False,
        )
        .select_related('discipline', 'department')
        .order_by('discipline_code', 'discipline__name')
    )
    visible_ids = _assignment_program_discipline_ids_for_user(user)
    if visible_ids is not None:
        program_disciplines = program_disciplines.filter(pk__in=visible_ids)

    if query:
        program_disciplines = program_disciplines.filter(
            Q(discipline__name__icontains=query.strip())
            | Q(discipline_code__icontains=query.strip()),
        )

    program_disciplines = list(program_disciplines)
    if not program_disciplines:
        return []

    pd_ids = [pd.id for pd in program_disciplines]

    assignments = TeacherProgramDiscipline.objects.filter(
        program_discipline_id__in=pd_ids,
    ).select_related('teacher').prefetch_related('teacher__departments')
    if not can_manage_teacher_assignments(user):
        assignments = assignments.filter(teacher=teacher)

    by_pd: dict[int, dict] = {pd_id: {'is_assigned': False, 'others': []} for pd_id in pd_ids}
    for link in assignments:
        bucket = by_pd[link.program_discipline_id]
        if teacher is not None and link.teacher_id == teacher.id:
            bucket['is_assigned'] = True
        else:
            bucket['others'].append(link.teacher.full_name)

    availability = get_assignment_availability(user, teacher, program_disciplines)
    rows = []
    for pd in program_disciplines:
        bucket = by_pd[pd.id]
        bucket['others'].sort()
        row_availability = availability.get(pd.id, {})
        rows.append({
            'id': pd.id,
            'discipline_name': pd.discipline.name,
            'discipline_code': pd.discipline_code,
            'discipline_display_name': pd.discipline_display_name,
            'department': pd.department.short_name if pd.department_id else '',
            'is_active_in_plan': pd.is_active_in_plan,
            'is_assigned': bucket['is_assigned'],
            'other_teachers': ', '.join(bucket['others']) if bucket['others'] else '',
            'can_assign': bool(row_availability.get('can_assign')),
            'cannot_assign_reason': row_availability.get('cannot_assign_reason', ''),
        })

    rows.sort(
        key=lambda row: (
            0 if row['is_assigned'] else 1 if row['can_assign'] else 2,
            row['discipline_code'] or '',
            row['discipline_name'].lower(),
        )
    )
    return rows


class TeachersDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'teachers/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        per_page = get_per_page(self.request)
        active_teacher, can_change_active = _resolve_active_teacher(self.request)
        can_manage_directory = is_staff_or_superuser(self.request.user)

        departments_qs = Department.objects.select_related('head_teacher').order_by('number')
        teachers_qs = Teacher.objects.select_related('department').prefetch_related('departments').order_by('full_name')
        teacher_program_disciplines_qs = TeacherProgramDiscipline.objects.select_related(
            'teacher',
            'program_discipline__educational_program__program_profile',
            'program_discipline__educational_program__department',
            'program_discipline__discipline',
        ).filter(program_discipline__educational_program__is_deleted=False).order_by(
            'teacher__full_name',
            'program_discipline__educational_program__program_profile__code',
            'program_discipline__discipline__name',
        )
        if is_senior_teacher(self.request.user) and not is_superuser_or_platform_admin(self.request.user):
            teachers_qs = filter_teachers_for_assignment(self.request.user, teachers_qs)
            departments_qs = departments_qs.filter(pk__in=get_user_departments(self.request.user))
            teacher_program_disciplines_qs = teacher_program_disciplines_qs.filter(
                program_discipline__in=filter_program_disciplines_for_assignment(
                    self.request.user,
                    ProgramDiscipline.objects.all(),
                )
            )
        elif not can_manage_directory:
            if active_teacher is None:
                departments_qs = departments_qs.none()
                teachers_qs = teachers_qs.none()
                teacher_program_disciplines_qs = teacher_program_disciplines_qs.none()
            else:
                departments_qs = departments_qs.filter(
                    Q(pk=active_teacher.department_id)
                    | Q(teachers_by_membership=active_teacher)
                ).distinct()
                teachers_qs = teachers_qs.filter(pk=active_teacher.pk)
                teacher_program_disciplines_qs = teacher_program_disciplines_qs.filter(
                    teacher=active_teacher,
                )

        departments_page_obj = paginate_queryset(
            self.request,
            departments_qs,
            page_param='department_page',
            per_page=per_page,
        )
        teachers_page_obj = paginate_queryset(
            self.request,
            teachers_qs,
            page_param='teacher_page',
            per_page=per_page,
        )
        teacher_program_disciplines_page_obj = paginate_queryset(
            self.request,
            teacher_program_disciplines_qs,
            page_param='link_page',
            per_page=per_page,
        )

        context['departments'] = departments_page_obj.object_list
        context['teachers'] = teachers_page_obj.object_list
        context['teacher_program_disciplines'] = teacher_program_disciplines_page_obj.object_list
        context['departments_page_obj'] = departments_page_obj
        context['teachers_page_obj'] = teachers_page_obj
        context['teacher_program_disciplines_page_obj'] = teacher_program_disciplines_page_obj
        context['departments_query_params'] = query_params_without(self.request, 'department_page')
        context['teachers_query_params'] = query_params_without(self.request, 'teacher_page')
        context['teacher_program_disciplines_query_params'] = query_params_without(self.request, 'link_page')
        context['per_page_choices'] = PER_PAGE_CHOICES
        context['selected_per_page'] = per_page

        program_id_raw = self.request.GET.get('assignment_program', '').strip()
        active_program = None
        if program_id_raw and program_id_raw.isdigit():
            program_id = int(program_id_raw)
            if _program_is_visible_for_assignments(self.request.user, program_id):
                active_program = (
                    EducationalProgram.objects.select_related(
                        'program_profile', 'department'
                    ).filter(pk=program_id, is_deleted=False).first()
                )

        assignment_query = self.request.GET.get('assignment_q', '').strip()
        assignment_rows = _build_assignment_rows(
            active_teacher,
            active_program,
            assignment_query,
            self.request.user,
        )

        teachers_picker_qs = Teacher.objects.select_related('department').prefetch_related('departments').order_by('full_name')
        if can_change_active:
            teachers_picker_qs = filter_teachers_for_assignment(self.request.user, teachers_picker_qs)
        elif active_teacher is not None:
            teachers_picker_qs = teachers_picker_qs.filter(pk=active_teacher.id)

        context['assignment_active_teacher'] = active_teacher
        context['assignment_can_change_teacher'] = can_change_active
        context['assignment_can_edit'] = _user_can_assign(self.request.user, active_teacher)
        context['can_manage_teacher_directory'] = can_manage_directory
        context['can_manage_departments'] = is_superuser_or_platform_admin(self.request.user)
        context['can_delete_teachers'] = is_superuser_or_platform_admin(self.request.user)
        context['assignment_teachers'] = teachers_picker_qs
        context['assignment_active_program'] = active_program
        context['assignment_active_program_id'] = active_program.id if active_program else ''
        context['assignment_query'] = assignment_query
        context['assignment_rows'] = assignment_rows
        return context


class DepartmentListView(NamedListView):
    model = Department
    title = 'Кафедры'
    search_fields = ('number', 'short_name', 'full_name')
    list_columns = (
        ('ID', 'id'),
        ('Номер', 'number'),
        ('Краткое название', 'short_name'),
        ('Заведующий', 'head_teacher.full_name'),
    )
    create_url_name = 'teachers_department_create'
    detail_url_name = 'teachers_department_detail'
    update_url_name = 'teachers_department_update'
    delete_url_name = 'teachers_department_delete'

    def can_use_action(self, action):
        if action in {'add', 'change', 'delete'}:
            return is_superuser_or_platform_admin(self.request.user)
        return super().can_use_action(action)


class DepartmentDetailView(NamedDetailView):
    model = Department
    title = 'Карточка кафедры'
    list_url_name = 'teachers_department_list'
    update_url_name = 'teachers_department_update'
    delete_url_name = 'teachers_department_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Номер', 'number'),
        ('Краткое название', 'short_name'),
        ('Полное название', 'full_name'),
        ('Заведующий', 'head_teacher.full_name'),
    )


class DepartmentCreateView(NamedCreateView):
    model = Department
    form_class = DepartmentForm
    title = 'Создать кафедру'
    list_url_name = 'teachers_department_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)


class DepartmentUpdateView(NamedUpdateView):
    model = Department
    form_class = DepartmentForm
    title = 'Редактировать кафедру'
    list_url_name = 'teachers_department_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)


class DepartmentDeleteView(NamedDeleteView):
    model = Department
    title = 'Удалить кафедру'
    list_url_name = 'teachers_department_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)


class TeacherListView(NamedListView):
    model = Teacher
    title = 'Преподаватели'
    search_fields = (
        'full_name',
        'department__short_name',
        'departments__short_name',
        'user__username',
    )
    list_columns = (
        ('ID', 'id'),
        ('ФИО', 'full_name'),
        ('Пользователь', 'user.username'),
        ('Кафедры', 'departments_display'),
        ('Степень', 'academic_degree.name'),
        ('Звание', 'academic_title.name'),
    )
    create_url_name = 'teachers_teacher_create'
    detail_url_name = 'teachers_teacher_detail'
    update_url_name = 'teachers_teacher_update'
    delete_url_name = 'teachers_teacher_delete'

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related('department', 'user', 'academic_degree', 'academic_title')
            .prefetch_related('departments')
            .distinct()
        )
        if is_senior_teacher(self.request.user) and not is_superuser_or_platform_admin(self.request.user):
            queryset = filter_teachers_for_assignment(self.request.user, queryset)
        return queryset

    def can_change_object(self, obj):
        return super().can_change_object(obj) and can_manage_teacher(self.request.user, obj)

    def can_delete_object(self, obj):
        return super().can_delete_object(obj) and is_superuser_or_platform_admin(self.request.user)


class TeacherDetailView(NamedDetailView):
    model = Teacher
    title = 'Карточка преподавателя'
    list_url_name = 'teachers_teacher_list'
    update_url_name = 'teachers_teacher_update'
    delete_url_name = 'teachers_teacher_delete'
    detail_fields = (
        ('ID', 'id'),
        ('ФИО', 'full_name'),
        ('Пользователь', 'user.username'),
        ('Основная кафедра', 'department.short_name'),
        ('Кафедры', 'departments_display'),
        ('Учёная степень', 'academic_degree.name'),
        ('Учёное звание', 'academic_title.name'),
    )

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'department',
            'user',
            'academic_degree',
            'academic_title',
        ).prefetch_related('departments')
        if is_senior_teacher(self.request.user) and not is_superuser_or_platform_admin(self.request.user):
            queryset = filter_teachers_for_assignment(self.request.user, queryset)
        return queryset


class TeacherCreateView(NamedCreateView):
    model = Teacher
    form_class = TeacherForm
    title = 'Создать преподавателя'
    list_url_name = 'teachers_teacher_list'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs


class TeacherUpdateView(NamedUpdateView):
    model = Teacher
    form_class = TeacherForm
    title = 'Редактировать преподавателя'
    list_url_name = 'teachers_teacher_list'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs

    def get_queryset(self):
        queryset = super().get_queryset().select_related('department').prefetch_related('departments')
        if is_senior_teacher(self.request.user) and not is_superuser_or_platform_admin(self.request.user):
            queryset = filter_teachers_for_assignment(self.request.user, queryset)
        return queryset


class TeacherDeleteView(NamedDeleteView):
    model = Teacher
    title = 'Удалить преподавателя'
    list_url_name = 'teachers_teacher_list'

    def has_permission(self):
        return is_superuser_or_platform_admin(self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset().select_related('department').prefetch_related('departments')
        if is_senior_teacher(self.request.user) and not is_superuser_or_platform_admin(self.request.user):
            queryset = filter_teachers_for_assignment(self.request.user, queryset)
        return queryset


class TeacherProgramDisciplineListView(NamedListView):
    model = TeacherProgramDiscipline
    title = 'Привязки преподавателей к дисциплинам учебных планов'
    order_by = (
        'teacher__full_name',
        'program_discipline__educational_program__program_profile__code',
        'program_discipline__discipline_code',
        'program_discipline__discipline__name',
    )
    search_fields = (
        'teacher__full_name',
        'program_discipline__discipline__name',
        'program_discipline__discipline_code',
        'program_discipline__educational_program__program_profile__code',
    )
    list_columns = (
        ('ID', 'id'),
        ('Преподаватель', 'teacher.full_name'),
        ('Программа', 'program_discipline.educational_program'),
        ('Дисциплина', 'program_discipline.discipline_display_name'),
    )
    create_url_name = 'teachers_teacher_program_discipline_create'
    detail_url_name = 'teachers_teacher_program_discipline_detail'
    update_url_name = 'teachers_teacher_program_discipline_update'
    delete_url_name = 'teachers_teacher_program_discipline_delete'

    def get_queryset(self):
        queryset = super().get_queryset().filter(program_discipline__educational_program__is_deleted=False)
        if is_senior_teacher(self.request.user) and not is_superuser_or_platform_admin(self.request.user):
            queryset = queryset.filter(
                teacher__in=filter_teachers_for_assignment(self.request.user, Teacher.objects.all()),
                program_discipline__in=filter_program_disciplines_for_assignment(
                    self.request.user,
                    ProgramDiscipline.objects.all(),
                ),
            )
        return queryset

    def can_change_object(self, obj):
        return (
            super().can_change_object(obj)
            and can_assign_teacher_to_program_discipline(
                self.request.user,
                obj.teacher,
                obj.program_discipline,
            )
        )

    def can_delete_object(self, obj):
        return self.can_change_object(obj)


class TeacherProgramDisciplineDetailView(NamedDetailView):
    model = TeacherProgramDiscipline
    title = 'Карточка привязки преподавателя'
    list_url_name = 'teachers_teacher_program_discipline_list'
    update_url_name = 'teachers_teacher_program_discipline_update'
    delete_url_name = 'teachers_teacher_program_discipline_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Преподаватель', 'teacher.full_name'),
        ('Образовательная программа', 'program_discipline.educational_program'),
        ('Дисциплина', 'program_discipline.discipline_display_name'),
    )

    def get_queryset(self):
        queryset = super().get_queryset().filter(program_discipline__educational_program__is_deleted=False)
        if is_senior_teacher(self.request.user) and not is_superuser_or_platform_admin(self.request.user):
            queryset = queryset.filter(
                teacher__in=filter_teachers_for_assignment(self.request.user, Teacher.objects.all()),
                program_discipline__in=filter_program_disciplines_for_assignment(
                    self.request.user,
                    ProgramDiscipline.objects.all(),
                ),
            )
        return queryset


class TeacherProgramDisciplineCreateView(NamedCreateView):
    model = TeacherProgramDiscipline
    form_class = TeacherProgramDisciplineForm
    title = 'Назначить преподавателю дисциплину учебного плана'
    list_url_name = 'teachers_teacher_program_discipline_list'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs


class TeacherProgramDisciplineUpdateView(NamedUpdateView):
    model = TeacherProgramDiscipline
    form_class = TeacherProgramDisciplineForm
    title = 'Редактировать привязку преподавателя'
    list_url_name = 'teachers_teacher_program_discipline_list'

    def get_queryset(self):
        queryset = super().get_queryset().filter(program_discipline__educational_program__is_deleted=False)
        if is_senior_teacher(self.request.user) and not is_superuser_or_platform_admin(self.request.user):
            queryset = queryset.filter(
                teacher__in=filter_teachers_for_assignment(self.request.user, Teacher.objects.all()),
                program_discipline__in=filter_program_disciplines_for_assignment(
                    self.request.user,
                    ProgramDiscipline.objects.all(),
                ),
            )
        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs


class TeacherProgramDisciplineDeleteView(NamedDeleteView):
    model = TeacherProgramDiscipline
    title = 'Удалить привязку преподавателя'
    list_url_name = 'teachers_teacher_program_discipline_list'

    def get_queryset(self):
        queryset = super().get_queryset().filter(program_discipline__educational_program__is_deleted=False)
        if is_senior_teacher(self.request.user) and not is_superuser_or_platform_admin(self.request.user):
            queryset = queryset.filter(
                teacher__in=filter_teachers_for_assignment(self.request.user, Teacher.objects.all()),
                program_discipline__in=filter_program_disciplines_for_assignment(
                    self.request.user,
                    ProgramDiscipline.objects.all(),
                ),
            )
        return queryset


class TeacherAssignmentPanelView(LoginRequiredMixin, View):
    """
    AJAX-эндпоинт для перерисовки таблицы назначений.
    Используется при изменении программы или поиске по дисциплине,
    чтобы не перезагружать всю страницу dashboard.
    """
    template_name = 'teachers/_assignment_table.html'

    def get(self, request, *args, **kwargs):
        from django.shortcuts import render

        active_teacher, _ = _resolve_active_teacher(request)
        program_id_raw = request.GET.get('assignment_program', '').strip()
        active_program = None
        if program_id_raw and program_id_raw.isdigit():
            program_id = int(program_id_raw)
            if _program_is_visible_for_assignments(request.user, program_id):
                active_program = (
                    EducationalProgram.objects.select_related('program_profile', 'department')
                    .filter(pk=program_id, is_deleted=False)
                    .first()
                )
        query = request.GET.get('assignment_q', '').strip()
        rows = _build_assignment_rows(active_teacher, active_program, query, request.user)
        return render(
            request,
            self.template_name,
            {
                'assignment_rows': rows,
                'assignment_active_program': active_program,
                'assignment_active_teacher': active_teacher,
                'assignment_can_edit': _user_can_assign(request.user, active_teacher),
            },
        )


@method_decorator(require_POST, name='dispatch')
class TeacherAssignmentToggleView(LoginRequiredMixin, View):
    """
    AJAX: создать или удалить связь TeacherProgramDiscipline для активного
    преподавателя по одной дисциплине учебного плана.

    Принимает JSON либо form-encoded:
      teacher_id (int) - кого назначаем
      program_discipline_id (int)
      assign (1 или 0) - 1 чтобы создать, 0 чтобы удалить

    Возвращает: {'ok': True, 'is_assigned': bool}
    """
    def post(self, request, *args, **kwargs):
        try:
            if request.content_type == 'application/json':
                payload = json.loads(request.body.decode('utf-8') or '{}')
            else:
                payload = request.POST
            teacher_id = int(payload.get('teacher_id'))
            program_discipline_id = int(payload.get('program_discipline_id'))
            assign_raw = str(payload.get('assign', '')).strip().lower()
            assign = assign_raw in {'1', 'true', 'yes', 'on'}
        except (TypeError, ValueError, json.JSONDecodeError):
            return HttpResponseBadRequest('Некорректные параметры запроса.')

        if not can_manage_teacher_assignments(request.user):
            raise PermissionDenied(
                'Назначения может менять только администратор или пользователь '
                'с правом управления назначениями.'
            )

        teacher = Teacher.objects.filter(pk=teacher_id).first()
        if teacher is None:
            return HttpResponseBadRequest('Преподаватель не найден.')

        if not _user_can_assign(request.user, teacher):
            raise PermissionDenied('Недостаточно прав для управления назначениями преподавателей.')

        program_discipline = ProgramDiscipline.objects.select_related('department', 'discipline').filter(
            pk=program_discipline_id,
            educational_program__is_deleted=False,
        ).first()
        if program_discipline is None:
            return HttpResponseBadRequest('Дисциплина учебного плана не найдена.')

        if not can_assign_teacher_to_program_discipline(request.user, teacher, program_discipline):
            return JsonResponse(
                {
                    'ok': False,
                    'error': assignment_denial_reason(request.user, teacher, program_discipline),
                },
                status=403,
            )

        with transaction.atomic():
            if assign:
                TeacherProgramDiscipline.objects.get_or_create(
                    teacher=teacher,
                    program_discipline_id=program_discipline_id,
                )
                is_assigned = True
            else:
                TeacherProgramDiscipline.objects.filter(
                    teacher=teacher,
                    program_discipline_id=program_discipline_id,
                ).delete()
                is_assigned = False

        return JsonResponse({'ok': True, 'is_assigned': is_assigned})
