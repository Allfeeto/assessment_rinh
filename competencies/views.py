from django.http import JsonResponse

from core.view_helpers import (
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
)
from disciplines.models import ProgramDiscipline

from .forms import CompetenceForm, DisciplineCompetenceForm
from .models import Competence, DisciplineCompetence


class CompetenceListView(NamedListView):
    model = Competence
    title = 'Компетенции'
    search_fields = ('code', 'name', 'educational_program__program_profile__code')
    list_columns = (
        ('ID', 'id'),
        ('Код', 'code'),
        ('Наименование', 'name'),
        ('Тип', 'competence_type.name'),
        ('Программа', 'educational_program'),
    )
    create_url_name = 'competencies_competence_create'
    detail_url_name = 'competencies_competence_detail'
    update_url_name = 'competencies_competence_update'
    delete_url_name = 'competencies_competence_delete'


class CompetenceDetailView(NamedDetailView):
    model = Competence
    title = 'Карточка компетенции'
    list_url_name = 'competencies_competence_list'
    update_url_name = 'competencies_competence_update'
    delete_url_name = 'competencies_competence_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Код', 'code'),
        ('Наименование', 'name'),
        ('Тип', 'competence_type.name'),
        ('Программа', 'educational_program'),
    )


class CompetenceCreateView(NamedCreateView):
    model = Competence
    form_class = CompetenceForm
    title = 'Создать компетенцию'
    list_url_name = 'competencies_competence_list'


class CompetenceUpdateView(NamedUpdateView):
    model = Competence
    form_class = CompetenceForm
    title = 'Редактировать компетенцию'
    list_url_name = 'competencies_competence_list'


class CompetenceDeleteView(NamedDeleteView):
    model = Competence
    title = 'Удалить компетенцию'
    list_url_name = 'competencies_competence_list'


class DisciplineCompetenceListView(NamedListView):
    model = DisciplineCompetence
    title = 'Матрица дисциплина → компетенция'
    search_fields = (
        'program_discipline__discipline__name',
        'competence__code',
        'competence__name',
    )
    list_columns = (
        ('ID', 'id'),
        ('Дисциплина учебного плана', 'program_discipline'),
        ('Компетенция', 'competence'),
    )
    create_url_name = 'competencies_discipline_competence_create'
    detail_url_name = 'competencies_discipline_competence_detail'
    update_url_name = 'competencies_discipline_competence_update'
    delete_url_name = 'competencies_discipline_competence_delete'


class DisciplineCompetenceDetailView(NamedDetailView):
    model = DisciplineCompetence
    title = 'Карточка связи дисциплины и компетенции'
    list_url_name = 'competencies_discipline_competence_list'
    update_url_name = 'competencies_discipline_competence_update'
    delete_url_name = 'competencies_discipline_competence_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Дисциплина учебного плана', 'program_discipline'),
        ('Компетенция', 'competence'),
    )


class DisciplineCompetenceCreateView(NamedCreateView):
    model = DisciplineCompetence
    form_class = DisciplineCompetenceForm
    title = 'Создать связь дисциплины и компетенции'
    list_url_name = 'competencies_discipline_competence_list'


class DisciplineCompetenceUpdateView(NamedUpdateView):
    model = DisciplineCompetence
    form_class = DisciplineCompetenceForm
    title = 'Редактировать связь дисциплины и компетенции'
    list_url_name = 'competencies_discipline_competence_list'


class DisciplineCompetenceDeleteView(NamedDeleteView):
    model = DisciplineCompetence
    title = 'Удалить связь дисциплины и компетенции'
    list_url_name = 'competencies_discipline_competence_list'


def competences_by_program_discipline(request):
    program_discipline_id = request.GET.get('program_discipline_id')
    queryset = Competence.objects.order_by('code')
    if program_discipline_id:
        educational_program_id = (
            ProgramDiscipline.objects.filter(pk=program_discipline_id)
            .values_list('educational_program_id', flat=True)
            .first()
        )
        if educational_program_id:
            queryset = queryset.filter(educational_program_id=educational_program_id)
        else:
            queryset = queryset.none()

    data = [{'id': obj.id, 'label': f'{obj.code} — {obj.name}'} for obj in queryset]
    return JsonResponse({'results': data})
