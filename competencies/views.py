from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.views.generic import TemplateView

from assessment.models import AssessmentItem, AssessmentItemCompetence
from programs.models import EducationalProgram

from core.view_helpers import (
    PER_PAGE_CHOICES,
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
    get_per_page,
)
from disciplines.models import ProgramDiscipline

from .forms import CompetenceForm, DisciplineCompetenceForm
from .models import Competence, DisciplineCompetence


class CompetenciesDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'competencies/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        educational_program_id = self.request.GET.get('educational_program', '').strip()
        discipline_id = self.request.GET.get('discipline', '').strip()
        competence_id = self.request.GET.get('competence', '').strip()
        search = self.request.GET.get('q', '').strip()
        per_page = get_per_page(self.request)

        competence_disciplines_count = (
            DisciplineCompetence.objects.filter(competence=OuterRef('pk'))
            .order_by()
            .values('competence')
            .annotate(total=Count('id'))
            .values('total')
        )
        competence_items_count = (
            AssessmentItemCompetence.objects.filter(competence=OuterRef('pk'))
            .order_by()
            .values('competence')
            .annotate(total=Count('assessment_item_id', distinct=True))
            .values('total')
        )

        competences_qs = Competence.objects.select_related(
            'competence_type',
            'educational_program__program_profile',
        ).annotate(
            disciplines_count=Coalesce(
                Subquery(competence_disciplines_count, output_field=IntegerField()),
                0,
            ),
            items_count=Coalesce(
                Subquery(competence_items_count, output_field=IntegerField()),
                0,
            ),
        ).order_by('educational_program__program_profile__code', 'code')

        if educational_program_id:
            competences_qs = competences_qs.filter(educational_program_id=educational_program_id)
        if discipline_id:
            linked_competence_ids = DisciplineCompetence.objects.filter(
                program_discipline__discipline_id=discipline_id,
            )
            if educational_program_id:
                linked_competence_ids = linked_competence_ids.filter(
                    program_discipline__educational_program_id=educational_program_id,
                )
            competences_qs = competences_qs.filter(
                id__in=linked_competence_ids.values_list('competence_id', flat=True)
            )
        if competence_id:
            competences_qs = competences_qs.filter(pk=competence_id)
        if search:
            competences_qs = competences_qs.filter(Q(code__icontains=search) | Q(name__icontains=search))

        # Сколько заданий внутри (program_discipline, competence) реально проверяет
        # эту компетенцию (через AssessmentItemCompetence). Считаем подзапросом, чтобы
        # не дублировать строки множественными JOIN’ами.
        link_items_count = (
            AssessmentItemCompetence.objects.filter(
                competence_id=OuterRef('competence_id'),
                assessment_item__program_discipline_id=OuterRef('program_discipline_id'),
            )
            .order_by()
            .values('competence_id')
            .annotate(total=Count('assessment_item_id', distinct=True))
            .values('total')
        )

        discipline_competences_qs = DisciplineCompetence.objects.select_related(
            'program_discipline__discipline',
            'program_discipline__educational_program__program_profile',
            'competence__competence_type',
            'competence',
        ).annotate(
            items_count=Coalesce(
                Subquery(link_items_count, output_field=IntegerField()),
                0,
            ),
        ).order_by(
            'program_discipline__educational_program__program_profile__code',
            'program_discipline__discipline__name',
            'competence__code',
        )

        if educational_program_id:
            discipline_competences_qs = discipline_competences_qs.filter(
                program_discipline__educational_program_id=educational_program_id
            )
        if competence_id:
            discipline_competences_qs = discipline_competences_qs.filter(competence_id=competence_id)
        discipline_options = []
        discipline_options_qs = ProgramDiscipline.objects.select_related('discipline')
        if educational_program_id:
            discipline_options_qs = discipline_options_qs.filter(
                educational_program_id=educational_program_id
            )
        if competence_id:
            discipline_options_qs = discipline_options_qs.filter(
                discipline_competences__competence_id=competence_id
            )
        discipline_options = list(
            discipline_options_qs.order_by('discipline__name').values(
                'discipline_id',
                'discipline__name',
            ).distinct()
        )
        valid_discipline_ids = {str(item['discipline_id']) for item in discipline_options}
        if discipline_id and discipline_id not in valid_discipline_ids:
            discipline_id = ''
        if discipline_id:
            discipline_competences_qs = discipline_competences_qs.filter(
                program_discipline__discipline_id=discipline_id
            )

        selected_program = (
            EducationalProgram.objects.select_related('program_profile', 'department')
            .filter(pk=educational_program_id)
            .first()
            if educational_program_id
            else None
        )
        educational_program_options = (
            EducationalProgram.objects.filter(pk=selected_program.pk)
            if selected_program
            else EducationalProgram.objects.none()
        )
        competence_options = (
            Competence.objects.filter(pk=competence_id)
            if competence_id
            else Competence.objects.none()
        )

        competences_paginator = Paginator(competences_qs, per_page)
        competences_page_obj = competences_paginator.get_page(self.request.GET.get('comp_page') or 1)

        discipline_competences_paginator = Paginator(discipline_competences_qs, per_page)
        discipline_competences_page_obj = discipline_competences_paginator.get_page(
            self.request.GET.get('link_page') or 1
        )

        selected_discipline_name = None
        if discipline_id:
            for option in discipline_options:
                if str(option['discipline_id']) == discipline_id:
                    selected_discipline_name = option['discipline__name']
                    break

        discipline_competence_competences = []
        if discipline_id:
            discipline_competence_competences = list(
                discipline_competences_qs.values(
                    'competence__code',
                    'competence__name',
                    'competence__competence_type__name',
                ).distinct().order_by('competence__code')
            )

        params = self.request.GET.copy()
        competences_params = params.copy()
        competences_params.pop('comp_page', None)
        links_params = params.copy()
        links_params.pop('link_page', None)

        context['educational_programs'] = educational_program_options
        context['discipline_options'] = discipline_options
        context['selected_program'] = educational_program_id
        context['selected_discipline'] = discipline_id
        context['selected_competence'] = competence_id
        context['selected_discipline_name'] = selected_discipline_name
        context['search_query'] = search
        context['competence_options'] = competence_options
        context['competences'] = competences_page_obj.object_list
        context['discipline_competences'] = discipline_competences_page_obj.object_list
        context['discipline_competence_competences'] = discipline_competence_competences
        context['competences_page_obj'] = competences_page_obj
        context['discipline_competences_page_obj'] = discipline_competences_page_obj
        context['competences_query_params'] = competences_params.urlencode()
        context['discipline_competences_query_params'] = links_params.urlencode()
        context['per_page_choices'] = PER_PAGE_CHOICES
        context['selected_per_page'] = per_page
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


@login_required
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
