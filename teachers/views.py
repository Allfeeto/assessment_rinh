from django.contrib.auth.mixins import LoginRequiredMixin
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

from .forms import DepartmentForm, TeacherForm, TeacherProgramDisciplineForm
from .models import Department, Teacher, TeacherProgramDiscipline


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
