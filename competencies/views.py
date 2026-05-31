from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.views.generic import TemplateView

from assessment.access import program_discipline_queryset_for_user
from assessment.models import AssessmentItem
from assessment.selectors import (
    count_items_by_competence,
    count_items_by_program_discipline_competence,
)
from core.permissions import is_domain_manager
from programs.models import EducationalProgram

from core.view_helpers import (
    PER_PAGE_CHOICES,
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
    get_per_page,
    paginate_queryset,
)
from disciplines.models import ProgramDiscipline

from .forms import CompetenceForm, DisciplineCompetenceForm
from .lookups import lookup_competence
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
        can_manage_competencies = is_domain_manager(self.request.user)
        program_discipline_scope = program_discipline_queryset_for_user(self.request.user)

        competence_disciplines_count = (
            DisciplineCompetence.objects.filter(
                competence=OuterRef('pk'),
                program_discipline__educational_program__is_deleted=False,
            )
            .order_by()
            .values('competence')
            .annotate(total=Count('id'))
            .values('total')
        )

        competences_qs = Competence.objects.select_related(
            'competence_type',
            'educational_program__program_profile',
        ).filter(educational_program__is_deleted=False)
        if not can_manage_competencies:
            competences_qs = competences_qs.filter(
                educational_program__program_disciplines__in=program_discipline_scope,
            ).distinct()

        competences_qs = competences_qs.annotate(
            disciplines_count=Coalesce(
                Subquery(competence_disciplines_count, output_field=IntegerField()),
                0,
            ),
        ).order_by('educational_program__program_profile__code', 'code')

        if educational_program_id:
            competences_qs = competences_qs.filter(educational_program_id=educational_program_id)
        if discipline_id:
            linked_competence_ids = DisciplineCompetence.objects.filter(
                program_discipline__discipline_id=discipline_id,
                program_discipline__educational_program__is_deleted=False,
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

        discipline_competences_qs = DisciplineCompetence.objects.select_related(
            'program_discipline__discipline',
            'program_discipline__department',
            'program_discipline__educational_program__program_profile',
            'competence__competence_type',
            'competence',
        ).filter(
            program_discipline__educational_program__is_deleted=False,
            program_discipline__in=program_discipline_scope,
        ).order_by(
            'program_discipline__educational_program__program_profile__code',
            'program_discipline__discipline_code',
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
        discipline_options_qs = program_discipline_scope.select_related('discipline')
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
        # Если выбранная дисциплина не входит в options текущей программы —
        # не стираем её, а добавляем в options отдельной записью, чтобы UI
        # сохранял выбор. Фильтр всё равно применяется ниже.
        valid_discipline_ids = {str(item['discipline_id']) for item in discipline_options}
        if (
            can_manage_competencies
            and discipline_id
            and discipline_id not in valid_discipline_ids
            and discipline_id.isdigit()
        ):
            from disciplines.models import Discipline as _Discipline
            extra_name = (
                _Discipline.objects.filter(pk=int(discipline_id))
                .values_list('name', flat=True)
                .first()
            )
            if extra_name:
                discipline_options.append({
                    'discipline_id': int(discipline_id),
                    'discipline__name': extra_name,
                })
        if discipline_id:
            discipline_competences_qs = discipline_competences_qs.filter(
                program_discipline__discipline_id=discipline_id
            )

        selected_program = (
            EducationalProgram.objects.select_related('program_profile', 'department')
            .filter(
                pk=educational_program_id,
                is_deleted=False,
                program_disciplines__in=program_discipline_scope,
            )
            .distinct()
            .first()
            if educational_program_id
            else None
        )
        educational_program_options = (
            EducationalProgram.objects.filter(pk=selected_program.pk, is_deleted=False)
            if selected_program
            else EducationalProgram.objects.none()
        )
        competence_options = (
            Competence.objects.filter(pk=competence_id, educational_program__is_deleted=False)
            if competence_id
            else Competence.objects.none()
        )

        competences_page_obj = paginate_queryset(
            self.request,
            competences_qs,
            page_param='comp_page',
            per_page=per_page,
        )
        competences_page = list(competences_page_obj.object_list)

        discipline_competences_page_obj = paginate_queryset(
            self.request,
            discipline_competences_qs,
            page_param='link_page',
            per_page=per_page,
        )
        discipline_competences_page = list(discipline_competences_page_obj.object_list)

        item_scope = AssessmentItem.objects.filter(
            program_discipline__educational_program__is_deleted=False,
            program_discipline__in=program_discipline_scope,
        )
        if educational_program_id:
            item_scope = item_scope.filter(program_discipline__educational_program_id=educational_program_id)
        if discipline_id:
            item_scope = item_scope.filter(program_discipline__discipline_id=discipline_id)

        competence_counts = count_items_by_competence(
            item_scope.values('pk'),
            [competence.id for competence in competences_page],
        )
        for competence in competences_page:
            competence.items_count = competence_counts.get(competence.id, 0)

        link_counts = count_items_by_program_discipline_competence(
            item_scope.values('pk'),
            [
                (link.program_discipline_id, link.competence_id)
                for link in discipline_competences_page
            ],
        )
        for link in discipline_competences_page:
            link.items_count = link_counts.get((link.program_discipline_id, link.competence_id), 0)

        competences_page_obj.object_list = competences_page
        discipline_competences_page_obj.object_list = discipline_competences_page

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
        context['competences'] = competences_page
        context['discipline_competences'] = discipline_competences_page
        context['discipline_competence_competences'] = discipline_competence_competences
        context['competences_page_obj'] = competences_page_obj
        context['discipline_competences_page_obj'] = discipline_competences_page_obj
        context['competences_query_params'] = competences_params.urlencode()
        context['discipline_competences_query_params'] = links_params.urlencode()
        context['per_page_choices'] = PER_PAGE_CHOICES
        context['selected_per_page'] = per_page
        context['can_manage_competencies'] = can_manage_competencies
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

    def get_queryset(self):
        return super().get_queryset().filter(educational_program__is_deleted=False)


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

    def get_queryset(self):
        return super().get_queryset().filter(educational_program__is_deleted=False)


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

    def get_queryset(self):
        return super().get_queryset().filter(educational_program__is_deleted=False)


class CompetenceDeleteView(NamedDeleteView):
    model = Competence
    title = 'Удалить компетенцию'
    list_url_name = 'competencies_competence_list'

    def get_queryset(self):
        return super().get_queryset().filter(educational_program__is_deleted=False)


class DisciplineCompetenceListView(NamedListView):
    model = DisciplineCompetence
    title = 'Матрица дисциплина → компетенция'
    search_fields = (
        'program_discipline__discipline__name',
        'program_discipline__discipline_code',
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

    def get_queryset(self):
        return super().get_queryset().filter(program_discipline__educational_program__is_deleted=False)


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

    def get_queryset(self):
        return super().get_queryset().filter(program_discipline__educational_program__is_deleted=False)


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

    def get_queryset(self):
        return super().get_queryset().filter(program_discipline__educational_program__is_deleted=False)


class DisciplineCompetenceDeleteView(NamedDeleteView):
    model = DisciplineCompetence
    title = 'Удалить связь дисциплины и компетенции'
    list_url_name = 'competencies_discipline_competence_list'

    def get_queryset(self):
        return super().get_queryset().filter(program_discipline__educational_program__is_deleted=False)


@login_required
def competences_by_program_discipline(request):
    # Deprecated compatibility endpoint for assessment/form.html.
    # Replacement: /core/lookup/?kind=competence&program_discipline_id=<id>&linked_only=1.
    # Remove after the assessment form checkbox refresh is migrated to the generic lookup client.
    return JsonResponse({'results': lookup_competence(request, query='', selected_id=None, limit=None)})
