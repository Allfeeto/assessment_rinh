from __future__ import annotations

from django.db.models import Count, Q

from assessment.access import program_discipline_queryset_for_user
from assessment.models import AssessmentItem
from assessment.selectors import (
    count_items_by_competence,
    count_items_by_program_discipline_competence,
    filter_items_by_competence,
)
from assessment.services import get_item_type_ui_name
from competencies.models import Competence, DisciplineCompetence
from core.models import AssessmentItemType
from core.view_helpers import PER_PAGE_CHOICES, get_per_page, paginate_queryset, query_params_without
from disciplines.models import Discipline
from programs.models import EducationalProgram


def build_reports_dashboard_context(request, form) -> dict:
    cleaned = form.cleaned_data if form.is_valid() else {}
    per_page = get_per_page(request)

    educational_program = cleaned.get('educational_program')
    discipline = cleaned.get('discipline')
    competence = cleaned.get('competence')
    assessment_item_type = cleaned.get('assessment_item_type')

    program_discipline_scope = program_discipline_queryset_for_user(request.user)
    program_discipline_ids = program_discipline_scope.values_list('id', flat=True)
    program_ids = program_discipline_scope.values_list('educational_program_id', flat=True)
    discipline_ids = program_discipline_scope.values_list('discipline_id', flat=True)

    item_filters = Q(
        program_discipline__educational_program__is_deleted=False,
        program_discipline_id__in=program_discipline_ids,
    )
    if educational_program:
        item_filters &= Q(program_discipline__educational_program=educational_program)
    if discipline:
        item_filters &= Q(program_discipline__discipline=discipline)
    if assessment_item_type:
        item_filters &= Q(assessment_item_type=assessment_item_type)

    assessment_items = AssessmentItem.objects.filter(item_filters).distinct()
    if competence:
        assessment_items = filter_items_by_competence(assessment_items, competence.id)
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
        request,
        report_by_type_qs,
        page_param='type_page',
        per_page=per_page,
    )
    report_by_type = list(report_by_type_page_obj.object_list)
    for row in report_by_type:
        row['ui_name'] = get_item_type_ui_name(row.get('code') or row['name'])

    report_by_program_qs = (
        EducationalProgram.objects.active().select_related('program_profile', 'department')
        .filter(id__in=program_ids)
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
        request,
        report_by_program_qs,
        page_param='program_page',
        per_page=per_page,
    )
    report_by_program = list(report_by_program_page_obj.object_list)

    report_by_discipline_qs = (
        Discipline.objects.filter(id__in=discipline_ids).annotate(
            total=Count(
                'program_disciplines__assessment_items',
                filter=Q(
                    program_disciplines__assessment_items__id__in=filtered_item_ids,
                    program_disciplines__educational_program__is_deleted=False,
                ),
                distinct=True,
            )
        )
        .values('id', 'name', 'total')
        .order_by('name')
    )
    report_by_discipline_page_obj = paginate_queryset(
        request,
        report_by_discipline_qs,
        page_param='discipline_page',
        per_page=per_page,
    )
    report_by_discipline = list(report_by_discipline_page_obj.object_list)

    competence_coverage_qs = Competence.objects.select_related(
        'educational_program__program_profile',
        'competence_type',
    ).filter(
        educational_program__is_deleted=False,
        educational_program_id__in=program_ids,
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
        request,
        competence_coverage_qs,
        page_param='competence_page',
        per_page=per_page,
    )
    competence_coverage = list(competence_coverage_page_obj.object_list)
    competence_counts = count_items_by_competence(
        filtered_item_ids,
        [row['id'] for row in competence_coverage],
    )
    for row in competence_coverage:
        row['items_count'] = competence_counts.get(row['id'], 0)

    discipline_competence_qs = DisciplineCompetence.objects.select_related(
        'program_discipline__discipline',
        'competence',
    ).filter(
        program_discipline__educational_program__is_deleted=False,
        program_discipline_id__in=program_discipline_ids,
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
            'program_discipline__discipline_code',
            'program_discipline__discipline__name',
            'competence_id',
            'competence__code',
            'competence__name',
        )
        .order_by('program_discipline__discipline_code', 'program_discipline__discipline__name', 'competence__code')
    )
    discipline_competence_page_obj = paginate_queryset(
        request,
        discipline_competence_qs,
        page_param='matrix_page',
        per_page=per_page,
    )
    discipline_competence_report = list(discipline_competence_page_obj.object_list)
    matrix_counts = count_items_by_program_discipline_competence(
        filtered_item_ids,
        [
            (row['program_discipline_id'], row['competence_id'])
            for row in discipline_competence_report
        ],
    )
    for row in discipline_competence_report:
        discipline_code = row.get('program_discipline__discipline_code')
        discipline_name = row['program_discipline__discipline__name']
        row['discipline_label'] = (
            f'{discipline_code} — {discipline_name}'
            if discipline_code
            else discipline_name
        )
        row['items_count'] = matrix_counts.get(
            (row['program_discipline_id'], row['competence_id']),
            0,
        )

    return {
        'assessment_items_count': assessment_items.count(),
        'report_by_type': report_by_type,
        'report_by_program': report_by_program,
        'report_by_discipline': report_by_discipline,
        'competence_coverage': competence_coverage,
        'discipline_competence_report': discipline_competence_report,
        'per_page_choices': PER_PAGE_CHOICES,
        'selected_per_page': per_page,
        'report_by_type_page_obj': report_by_type_page_obj,
        'report_by_program_page_obj': report_by_program_page_obj,
        'report_by_discipline_page_obj': report_by_discipline_page_obj,
        'competence_coverage_page_obj': competence_coverage_page_obj,
        'discipline_competence_page_obj': discipline_competence_page_obj,
        'report_by_type_query_params': query_params_without(request, 'type_page'),
        'report_by_program_query_params': query_params_without(request, 'program_page'),
        'report_by_discipline_query_params': query_params_without(request, 'discipline_page'),
        'competence_coverage_query_params': query_params_without(request, 'competence_page'),
        'discipline_competence_query_params': query_params_without(request, 'matrix_page'),
    }
