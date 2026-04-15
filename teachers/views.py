from django.views.generic import TemplateView

from core.view_helpers import (
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
)

from .forms import DepartmentForm, TeacherForm
from .models import Department, Teacher


class TeachersDashboardView(TemplateView):
    template_name = 'teachers/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.select_related('head_teacher').order_by('number')
        context['teachers'] = Teacher.objects.select_related('department').order_by('full_name')
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
    search_fields = ('full_name', 'department__short_name')
    list_columns = (
        ('ID', 'id'),
        ('ФИО', 'full_name'),
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
