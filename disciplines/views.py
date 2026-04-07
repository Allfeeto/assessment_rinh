from django.http import JsonResponse

from core.view_helpers import (
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
)

from .forms import DisciplineForm, ProgramDisciplineForm
from .models import Discipline, ProgramDiscipline


class DisciplineListView(NamedListView):
    model = Discipline
    title = 'Дисциплины'
    search_fields = ('name',)
    list_columns = (('ID', 'id'), ('Наименование', 'name'))
    create_url_name = 'disciplines_discipline_create'
    detail_url_name = 'disciplines_discipline_detail'
    update_url_name = 'disciplines_discipline_update'
    delete_url_name = 'disciplines_discipline_delete'


class DisciplineDetailView(NamedDetailView):
    model = Discipline
    title = 'Карточка дисциплины'
    list_url_name = 'disciplines_discipline_list'
    update_url_name = 'disciplines_discipline_update'
    delete_url_name = 'disciplines_discipline_delete'
    detail_fields = (('ID', 'id'), ('Наименование', 'name'))


class DisciplineCreateView(NamedCreateView):
    model = Discipline
    form_class = DisciplineForm
    title = 'Создать дисциплину'
    list_url_name = 'disciplines_discipline_list'


class DisciplineUpdateView(NamedUpdateView):
    model = Discipline
    form_class = DisciplineForm
    title = 'Редактировать дисциплину'
    list_url_name = 'disciplines_discipline_list'


class DisciplineDeleteView(NamedDeleteView):
    model = Discipline
    title = 'Удалить дисциплину'
    list_url_name = 'disciplines_discipline_list'


class ProgramDisciplineListView(NamedListView):
    model = ProgramDiscipline
    title = 'Дисциплины учебных планов'
    search_fields = (
        'discipline__name',
        'educational_program__program_profile__code',
        'educational_program__program_profile__name',
    )
    list_columns = (
        ('ID', 'id'),
        ('Программа', 'educational_program'),
        ('Дисциплина', 'discipline.name'),
    )
    create_url_name = 'disciplines_program_discipline_create'
    detail_url_name = 'disciplines_program_discipline_detail'
    update_url_name = 'disciplines_program_discipline_update'
    delete_url_name = 'disciplines_program_discipline_delete'


class ProgramDisciplineDetailView(NamedDetailView):
    model = ProgramDiscipline
    title = 'Карточка дисциплины учебного плана'
    list_url_name = 'disciplines_program_discipline_list'
    update_url_name = 'disciplines_program_discipline_update'
    delete_url_name = 'disciplines_program_discipline_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Программа', 'educational_program'),
        ('Дисциплина', 'discipline.name'),
    )


class ProgramDisciplineCreateView(NamedCreateView):
    model = ProgramDiscipline
    form_class = ProgramDisciplineForm
    title = 'Создать дисциплину учебного плана'
    list_url_name = 'disciplines_program_discipline_list'


class ProgramDisciplineUpdateView(NamedUpdateView):
    model = ProgramDiscipline
    form_class = ProgramDisciplineForm
    title = 'Редактировать дисциплину учебного плана'
    list_url_name = 'disciplines_program_discipline_list'


class ProgramDisciplineDeleteView(NamedDeleteView):
    model = ProgramDiscipline
    title = 'Удалить дисциплину учебного плана'
    list_url_name = 'disciplines_program_discipline_list'


def program_discipline_by_program(request):
    educational_program_id = request.GET.get('educational_program_id')
    queryset = ProgramDiscipline.objects.select_related('discipline').order_by('discipline__name')
    if educational_program_id:
        queryset = queryset.filter(educational_program_id=educational_program_id)

    data = [
        {
            'id': obj.id,
            'label': f'{obj.educational_program} | {obj.discipline.name}',
            'discipline_id': obj.discipline_id,
        }
        for obj in queryset
    ]
    return JsonResponse({'results': data})