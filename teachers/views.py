import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

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
    can_change = bool(user.is_superuser or user.is_staff)

    requested_id = request.GET.get('teacher') or request.POST.get('teacher')
    if can_change and requested_id and str(requested_id).isdigit():
        teacher = Teacher.objects.filter(pk=int(requested_id)).first()
        if teacher is not None:
            return teacher, True

    if profile is not None:
        return profile, can_change

    if can_change:
        teacher = Teacher.objects.order_by('full_name').first()
        return teacher, True

    return None, False


def _user_can_assign(user, teacher):
    """Может ли пользователь назначать/снимать активного преподавателя."""
    if not user.is_authenticated or teacher is None:
        return False
    if user.is_superuser or user.is_staff:
        return True
    profile = getattr(user, 'teacher_profile', None)
    return profile is not None and profile.id == teacher.id


def _build_assignment_rows(teacher, educational_program, query):
    """
    Список ProgramDiscipline для активного преподавателя и выбранной программы.
    Возвращает список словарей: id, discipline_name, is_assigned (для активного teacher),
    other_teachers (строка с ФИО других назначенных).
    Сортировка: сначала назначенные, затем по алфавиту.
    """
    if educational_program is None:
        return []

    program_disciplines = (
        ProgramDiscipline.objects.filter(educational_program=educational_program)
        .select_related('discipline')
        .order_by('discipline__name')
    )

    if query:
        program_disciplines = program_disciplines.filter(
            discipline__name__icontains=query.strip(),
        )

    program_disciplines = list(program_disciplines)
    if not program_disciplines:
        return []

    pd_ids = [pd.id for pd in program_disciplines]

    assignments = TeacherProgramDiscipline.objects.filter(
        program_discipline_id__in=pd_ids,
    ).select_related('teacher')

    by_pd: dict[int, dict] = {pd_id: {'is_assigned': False, 'others': []} for pd_id in pd_ids}
    for link in assignments:
        bucket = by_pd[link.program_discipline_id]
        if teacher is not None and link.teacher_id == teacher.id:
            bucket['is_assigned'] = True
        else:
            bucket['others'].append(link.teacher.full_name)

    rows = []
    for pd in program_disciplines:
        bucket = by_pd[pd.id]
        bucket['others'].sort()
        rows.append({
            'id': pd.id,
            'discipline_name': pd.discipline.name,
            'is_assigned': bucket['is_assigned'],
            'other_teachers': ', '.join(bucket['others']) if bucket['others'] else '',
        })

    rows.sort(key=lambda row: (0 if row['is_assigned'] else 1, row['discipline_name'].lower()))
    return rows


class TeachersDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'teachers/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        per_page = get_per_page(self.request)
        departments_qs = Department.objects.select_related('head_teacher').order_by('number')
        teachers_qs = Teacher.objects.select_related('department').order_by('full_name')
        teacher_program_disciplines_qs = TeacherProgramDiscipline.objects.select_related(
            'teacher',
            'program_discipline__educational_program__program_profile',
            'program_discipline__educational_program__department',
            'program_discipline__discipline',
        ).order_by(
            'teacher__full_name',
            'program_discipline__educational_program__program_profile__code',
            'program_discipline__discipline__name',
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

        # Панель «Назначение преподавателей на дисциплины» — встроенная в dashboard.
        active_teacher, can_change_active = _resolve_active_teacher(self.request)

        program_id_raw = self.request.GET.get('assignment_program', '').strip()
        active_program = None
        if program_id_raw and program_id_raw.isdigit():
            active_program = (
                EducationalProgram.objects.select_related(
                    'program_profile', 'department'
                ).filter(pk=int(program_id_raw)).first()
            )

        assignment_query = self.request.GET.get('assignment_q', '').strip()
        assignment_rows = _build_assignment_rows(active_teacher, active_program, assignment_query)

        teachers_picker_qs = Teacher.objects.select_related('department').order_by('full_name')
        if not can_change_active and active_teacher is not None:
            teachers_picker_qs = teachers_picker_qs.filter(pk=active_teacher.id)

        context['assignment_active_teacher'] = active_teacher
        context['assignment_can_change_teacher'] = can_change_active
        context['assignment_can_edit'] = _user_can_assign(self.request.user, active_teacher)
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


class DepartmentUpdateView(NamedUpdateView):
    model = Department
    form_class = DepartmentForm
    title = 'Редактировать кафедру'
    list_url_name = 'teachers_department_list'


class DepartmentDeleteView(NamedDeleteView):
    model = Department
    title = 'Удалить кафедру'
    list_url_name = 'teachers_department_list'


class TeacherListView(NamedListView):
    model = Teacher
    title = 'Преподаватели'
    search_fields = ('full_name', 'department__short_name', 'user__username')
    list_columns = (
        ('ID', 'id'),
        ('ФИО', 'full_name'),
        ('Пользователь', 'user.username'),
        ('Кафедра', 'department.short_name'),
        ('Степень', 'academic_degree.name'),
        ('Звание', 'academic_title.name'),
    )
    create_url_name = 'teachers_teacher_create'
    detail_url_name = 'teachers_teacher_detail'
    update_url_name = 'teachers_teacher_update'
    delete_url_name = 'teachers_teacher_delete'


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
        ('Кафедра', 'department.short_name'),
        ('Учёная степень', 'academic_degree.name'),
        ('Учёное звание', 'academic_title.name'),
    )


class TeacherCreateView(NamedCreateView):
    model = Teacher
    form_class = TeacherForm
    title = 'Создать преподавателя'
    list_url_name = 'teachers_teacher_list'


class TeacherUpdateView(NamedUpdateView):
    model = Teacher
    form_class = TeacherForm
    title = 'Редактировать преподавателя'
    list_url_name = 'teachers_teacher_list'


class TeacherDeleteView(NamedDeleteView):
    model = Teacher
    title = 'Удалить преподавателя'
    list_url_name = 'teachers_teacher_list'


class TeacherProgramDisciplineListView(NamedListView):
    model = TeacherProgramDiscipline
    title = 'Привязки преподавателей к дисциплинам учебных планов'
    search_fields = (
        'teacher__full_name',
        'program_discipline__discipline__name',
        'program_discipline__educational_program__program_profile__code',
    )
    list_columns = (
        ('ID', 'id'),
        ('Преподаватель', 'teacher.full_name'),
        ('Программа', 'program_discipline.educational_program'),
        ('Дисциплина', 'program_discipline.discipline.name'),
    )
    create_url_name = 'teachers_teacher_program_discipline_create'
    detail_url_name = 'teachers_teacher_program_discipline_detail'
    update_url_name = 'teachers_teacher_program_discipline_update'
    delete_url_name = 'teachers_teacher_program_discipline_delete'


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
        ('Дисциплина', 'program_discipline.discipline.name'),
    )


class TeacherProgramDisciplineCreateView(NamedCreateView):
    model = TeacherProgramDiscipline
    form_class = TeacherProgramDisciplineForm
    title = 'Назначить преподавателю дисциплину учебного плана'
    list_url_name = 'teachers_teacher_program_discipline_list'


class TeacherProgramDisciplineUpdateView(NamedUpdateView):
    model = TeacherProgramDiscipline
    form_class = TeacherProgramDisciplineForm
    title = 'Редактировать привязку преподавателя'
    list_url_name = 'teachers_teacher_program_discipline_list'


class TeacherProgramDisciplineDeleteView(NamedDeleteView):
    model = TeacherProgramDiscipline
    title = 'Удалить привязку преподавателя'
    list_url_name = 'teachers_teacher_program_discipline_list'


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
            active_program = (
                EducationalProgram.objects.select_related('program_profile', 'department')
                .filter(pk=int(program_id_raw))
                .first()
            )
        query = request.GET.get('assignment_q', '').strip()
        rows = _build_assignment_rows(active_teacher, active_program, query)
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

        teacher = Teacher.objects.filter(pk=teacher_id).first()
        if teacher is None:
            return HttpResponseBadRequest('Преподаватель не найден.')

        if not _user_can_assign(request.user, teacher):
            raise PermissionDenied('Назначения может менять только сам преподаватель или администратор.')

        if not ProgramDiscipline.objects.filter(pk=program_discipline_id).exists():
            return HttpResponseBadRequest('Дисциплина учебного плана не найдена.')

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
