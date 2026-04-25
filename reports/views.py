from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Q
from django.views.generic import TemplateView

from assessment.models import AssessmentItem, AssessmentItemCompetence
from assessment.services import get_item_type_ui_name
from competencies.models import Competence, DisciplineCompetence
from core.models import AssessmentItemType
from core.view_helpers import PER_PAGE_CHOICES, get_per_page, paginate_queryset, query_params_without
from disciplines.models import Discipline
from programs.models import EducationalProgram

from .forms import ReportFilterForm


def _count_items_by_competence(filtered_item_ids, competence_ids):
    if not competence_ids:
        return {}

    primary_pairs = (
        AssessmentItem.objects.filter(
            id__in=filtered_item_ids,
            competence_id__in=competence_ids,
        )
        .annotate(
            competence_key=F('competence_id'),
            item_key=F('id'),
        )
        .values('competence_key', 'item_key')
    )
    linked_pairs = (
        AssessmentItemCompetence.objects.filter(
            assessment_item_id__in=filtered_item_ids,
            competence_id__in=competence_ids,
        )
        .annotate(
            competence_key=F('competence_id'),
            item_key=F('assessment_item_id'),
        )
        .values('competence_key', 'item_key')
    )

    grouped = {}
    for pair in primary_pairs.union(linked_pairs):
        grouped.setdefault(pair['competence_key'], set()).add(pair['item_key'])
    return {competence_id: len(item_ids) for competence_id, item_ids in grouped.items()}


def _count_items_by_program_discipline_competence(filtered_item_ids, pairs):
    if not pairs:
        return {}

    program_discipline_ids = {pair[0] for pair in pairs}
    competence_ids = {pair[1] for pair in pairs}

    primary_pairs = (
        AssessmentItem.objects.filter(
            id__in=filtered_item_ids,
            program_discipline_id__in=program_discipline_ids,
            competence_id__in=competence_ids,
        )
        .annotate(
            program_discipline_key=F('program_discipline_id'),
            competence_key=F('competence_id'),
            item_key=F('id'),
        )
        .values('program_discipline_key', 'competence_key', 'item_key')
    )
    linked_pairs = (
        AssessmentItemCompetence.objects.filter(
            assessment_item_id__in=filtered_item_ids,
            assessment_item__program_discipline_id__in=program_discipline_ids,
            competence_id__in=competence_ids,
        )
        .annotate(
            program_discipline_key=F('assessment_item__program_discipline_id'),
            competence_key=F('competence_id'),
            item_key=F('assessment_item_id'),
        )
        .values('program_discipline_key', 'competence_key', 'item_key')
    )

    grouped = {}
    for pair in primary_pairs.union(linked_pairs):
        key = (pair['program_discipline_key'], pair['competence_key'])
        grouped.setdefault(key, set()).add(pair['item_key'])
    return {key: len(item_ids) for key, item_ids in grouped.items()}


class ReportsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = ReportFilterForm(self.request.GET or None)
        cleaned = form.cleaned_data if form.is_valid() else {}
        per_page = get_per_page(self.request)

        educational_program = cleaned.get('educational_program')
        discipline = cleaned.get('discipline')
        competence = cleaned.get('competence')
        assessment_item_type = cleaned.get('assessment_item_type')

        item_filters = Q()
        if educational_program:
            item_filters &= Q(program_discipline__educational_program=educational_program)
        if discipline:
            item_filters &= Q(program_discipline__discipline=discipline)
        if assessment_item_type:
            item_filters &= Q(assessment_item_type=assessment_item_type)
        if competence:
            item_filters &= (
                Q(competence=competence) | Q(competence_links__competence=competence)
            )

        assessment_items = AssessmentItem.objects.filter(item_filters).distinct()
        filtered_item_ids = assessment_items.values('pk')

        report_by_type_qs = (
            AssessmentItemType.objects.annotate(
                total=Count(
                    'assessment_items',
                    filter=Q(assessment_items__id__in=filtered_item_ids),
                    distinct=True,
                )
            )
            .values('name', 'total')
            .order_by('name')
        )
        report_by_type_page_obj = paginate_queryset(
            self.request,
            report_by_type_qs,
            page_param='type_page',
            per_page=per_page,
        )
        report_by_type = list(report_by_type_page_obj.object_list)
        for row in report_by_type:
            row['ui_name'] = get_item_type_ui_name(row['name'])

        report_by_program_qs = (
            EducationalProgram.objects.select_related('program_profile', 'department')
            .annotate(
                total=Count(
                    'program_disciplines__assessment_items',
                    filter=Q(program_disciplines__assessment_items__id__in=filtered_item_ids),
                    distinct=True,
                )
            )
            .values(
                'id',
                'program_profile__code',
                'program_profile__name',
                'department__short_name',
                'admission_year',
                'total',
            )
            .order_by('program_profile__code', 'admission_year')
        )
        report_by_program_page_obj = paginate_queryset(
            self.request,
            report_by_program_qs,
            page_param='program_page',
            per_page=per_page,
        )
        report_by_program = list(report_by_program_page_obj.object_list)

        report_by_discipline_qs = (
            Discipline.objects.annotate(
                total=Count(
                    'program_disciplines__assessment_items',
                    filter=Q(program_disciplines__assessment_items__id__in=filtered_item_ids),
                    distinct=True,
                )
            )
            .values('id', 'name', 'total')
            .order_by('name')
        )
        report_by_discipline_page_obj = paginate_queryset(
            self.request,
            report_by_discipline_qs,
            page_param='discipline_page',
            per_page=per_page,
        )
        report_by_discipline = list(report_by_discipline_page_obj.object_list)

        competence_coverage_qs = Competence.objects.select_related(
            'educational_program__program_profile',
            'competence_type',
        )
        if educational_program:
            competence_coverage_qs = competence_coverage_qs.filter(educational_program=educational_program)
        if competence:
            competence_coverage_qs = competence_coverage_qs.filter(pk=competence.pk)

        competence_coverage_qs = (
            competence_coverage_qs.values(
                'id',
                'code',
                'name',
                'competence_type__name',
                'educational_program__program_profile__code',
            )
            .order_by('educational_program__program_profile__code', 'code')
        )
        competence_coverage_page_obj = paginate_queryset(
            self.request,
            competence_coverage_qs,
            page_param='competence_page',
            per_page=per_page,
        )
        competence_coverage = list(competence_coverage_page_obj.object_list)
        competence_counts = _count_items_by_competence(
            filtered_item_ids,
            [row['id'] for row in competence_coverage],
        )
        for row in competence_coverage:
            row['items_count'] = competence_counts.get(row['id'], 0)

        discipline_competence_qs = DisciplineCompetence.objects.select_related(
            'program_discipline__discipline',
            'competence',
        )
        if educational_program:
            discipline_competence_qs = discipline_competence_qs.filter(
                program_discipline__educational_program=educational_program
            )
        if discipline:
            discipline_competence_qs = discipline_competence_qs.filter(
                program_discipline__discipline=discipline
            )
        if competence:
            discipline_competence_qs = discipline_competence_qs.filter(competence=competence)

        discipline_competence_qs = (
            discipline_competence_qs.values(
                'program_discipline_id',
                'program_discipline__discipline__name',
                'competence_id',
                'competence__code',
                'competence__name',
            )
            .order_by('program_discipline__discipline__name', 'competence__code')
        )
        discipline_competence_page_obj = paginate_queryset(
            self.request,
            discipline_competence_qs,
            page_param='matrix_page',
            per_page=per_page,
        )
        discipline_competence_report = list(discipline_competence_page_obj.object_list)
        matrix_counts = _count_items_by_program_discipline_competence(
            filtered_item_ids,
            [
                (row['program_discipline_id'], row['competence_id'])
                for row in discipline_competence_report
            ],
        )
        for row in discipline_competence_report:
            row['items_count'] = matrix_counts.get(
                (row['program_discipline_id'], row['competence_id']),
                0,
            )

        context['form'] = form
        context['assessment_items_count'] = assessment_items.count()
        context['report_by_type'] = report_by_type
        context['report_by_program'] = report_by_program
        context['report_by_discipline'] = report_by_discipline
        context['competence_coverage'] = competence_coverage
        context['discipline_competence_report'] = discipline_competence_report
        context['per_page_choices'] = PER_PAGE_CHOICES
        context['selected_per_page'] = per_page
        context['report_by_type_page_obj'] = report_by_type_page_obj
        context['report_by_program_page_obj'] = report_by_program_page_obj
        context['report_by_discipline_page_obj'] = report_by_discipline_page_obj
        context['competence_coverage_page_obj'] = competence_coverage_page_obj
        context['discipline_competence_page_obj'] = discipline_competence_page_obj
        context['report_by_type_query_params'] = query_params_without(self.request, 'type_page')
        context['report_by_program_query_params'] = query_params_without(self.request, 'program_page')
        context['report_by_discipline_query_params'] = query_params_without(self.request, 'discipline_page')
        context['competence_coverage_query_params'] = query_params_without(self.request, 'competence_page')
        context['discipline_competence_query_params'] = query_params_without(self.request, 'matrix_page')
        return context
