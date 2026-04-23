from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.generic import TemplateView

from assessment.models import AssessmentItem
from programs.models import EducationalProgram

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


class CompetenciesDashboardView(TemplateView):
    template_name = 'competencies/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        educational_program_id = self.request.GET.get('educational_program', '').strip()
        discipline_id = self.request.GET.get('discipline', '').strip()
        search = self.request.GET.get('q', '').strip()

        competences_qs = Competence.objects.select_related(
            'competence_type',
            'educational_program__program_profile',
        ).annotate(
            disciplines_count=Count('discipline_competences', distinct=True),
        ).order_by('educational_program__program_profile__code', 'code')

        if educational_program_id:
            competences_qs = competences_qs.filter(educational_program_id=educational_program_id)
        if search:
            competences_qs = competences_qs.filter(Q(code__icontains=search) | Q(name__icontains=search))

        competences = list(competences_qs)
        for competence_obj in competences:
            competence_obj.items_count = (
                AssessmentItem.objects.filter(
                    Q(competence=competence_obj) | Q(competence_links__competence=competence_obj)
                )
                .distinct()
                .count()
            )

        discipline_competences_qs = DisciplineCompetence.objects.select_related(
            'program_discipline__discipline',
            'program_discipline__educational_program__program_profile',
            'competence__competence_type',
        ).order_by(
            'program_discipline__educational_program__program_profile__code',
            'program_discipline__discipline__name',
            'competence__code',
        )

        if educational_program_id:
            discipline_competences_qs = discipline_competences_qs.filter(
                program_discipline__educational_program_id=educational_program_id
            )
        if discipline_id:
            discipline_competences_qs = discipline_competences_qs.filter(
                program_discipline__discipline_id=discipline_id
            )

        discipline_competences = list(discipline_competences_qs)
        for link in discipline_competences:
            link.items_count = (
                AssessmentItem.objects.filter(program_discipline=link.program_discipline)
                .filter(
                    Q(competence=link.competence) | Q(competence_links__competence=link.competence)
                )
                .distinct()
                .count()
            )

        discipline_options = ProgramDiscipline.objects.select_related('discipline')
        if educational_program_id:
            discipline_options = discipline_options.filter(educational_program_id=educational_program_id)
        discipline_options = discipline_options.order_by('discipline__name').values(
            'discipline_id',
            'discipline__name',
        ).distinct()

        context['educational_programs'] = EducationalProgram.objects.select_related(
            'program_profile',
            'department',
        ).order_by('program_profile__code', 'admission_year')
        context['discipline_options'] = discipline_options
        context['selected_program'] = educational_program_id
        context['selected_discipline'] = discipline_id
        context['search_query'] = search
        context['competences'] = competences
        context['discipline_competences'] = discipline_competences
        return context


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
    linked_only = request.GET.get('linked_only') in {'1', 'true', 'True'}

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

        if linked_only:
            queryset = queryset.filter(discipline_competences__program_discipline_id=program_discipline_id)

    data = [{'id': obj.id, 'label': f'{obj.code} — {obj.name}'} for obj in queryset.distinct()]
    return JsonResponse({'results': data})
