from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.views.generic import TemplateView

from assessment.models import AssessmentItem
from assessment.services import get_item_type_ui_name
from competencies.models import Competence, DisciplineCompetence
from core.models import AssessmentItemType
from core.view_helpers import PER_PAGE_CHOICES, get_per_page, paginate_queryset, query_params_without
from disciplines.models import Discipline
from programs.models import EducationalProgram

from .forms import ReportFilterForm


def _count_items_by_competence(filtered_item_ids, competence_ids):
    """Сколько отфильтрованных заданий проверяют каждую компетенцию.

    Источников связи два — основная FK ``AssessmentItem.competence`` и таблица
    ``AssessmentItemCompetence``. Берём UNION одним запросом через ``Q`` и
    считаем уникальные пары (competence, item).
    """
    if not competence_ids:
        return {}

    rows = (
        AssessmentItem.objects.filter(
            Q(competence_id__in=competence_ids)
            | Q(competence_links__competence_id__in=competence_ids),
            id__in=filtered_item_ids,
        )
        .values('competence_id', 'competence_links__competence_id', 'id')
        .distinct()
    )

    grouped: dict[int, set[int]] = {}
    competence_ids_set = set(competence_ids)
    for row in rows:
        item_id = row['id']
        for key in (row['competence_id'], row['competence_links__competence_id']):
            if key in competence_ids_set:
                grouped.setdefault(key, set()).add(item_id)
    return {competence_id: len(items) for competence_id, items in grouped.items()}


def _count_items_by_program_discipline_competence(filtered_item_ids, pairs):
    """Аналогично _count_items_by_competence, но ключ — (program_discipline, competence)."""
    if not pairs:
        return {}

    program_discipline_ids = {pair[0] for pair in pairs}
    competence_ids = {pair[1] for pair in pairs}
    pair_set = set(pairs)

    rows = (
        AssessmentItem.objects.filter(
            Q(competence_id__in=competence_ids)
            | Q(competence_links__competence_id__in=competence_ids),
            id__in=filtered_item_ids,
            program_discipline_id__in=program_discipline_ids,
        )
        .values(
            'program_discipline_id',
            'competence_id',
            'competence_links__competence_id',
            'id',
        )
        .distinct()
    )

    grouped: dict[tuple[int, int], set[int]] = {}
    for row in rows:
        program_discipline_id = row['program_discipline_id']
        item_id = row['id']
        for key in (row['competence_id'], row['competence_links__competence_id']):
            if key is None:
                continue
            pair = (program_discipline_id, key)
            if pair in pair_set:
                grouped.setdefault(pair, set()).add(item_id)
    return {pair: len(items) for pair, items in grouped.items()}


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
            .values('code', 'name', 'total')
            .order_by('code', 'name')
        )
        report_by_type_page_obj = paginate_queryset(
            self.request,
            report_by_type_qs,
            page_param='type_page',
            per_page=per_page,
        )
        report_by_type = list(report_by_type_page_obj.object_list)
        for row in report_by_type:
            row['ui_name'] = get_item_type_ui_name(row.get('code') or row['name'])

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
