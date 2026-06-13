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
from core.view_helpers import PER_PAGE_CHOICES, compact_queryset_block, get_per_page
from disciplines.models import Discipline
from programs.models import EducationalProgram


def build_reports_dashboard_context(request, form, *, fragment='') -> dict:
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

    context = {'per_page_choices': PER_PAGE_CHOICES, 'selected_per_page': per_page}
    if not fragment:
        context['assessment_items_count'] = assessment_items.count()

    if fragment in {'', 'report_by_type'}:
        queryset = (
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
        block = compact_queryset_block(request, queryset, prefix='report_by_type', page_size=per_page)
        rows = list(block['items'])
        for row in rows:
            row['ui_name'] = get_item_type_ui_name(row.get('code') or row['name'])
        block['items'] = rows
        context['report_by_type_block'] = block

    if fragment in {'', 'report_by_program'}:
        queryset = (
            EducationalProgram.objects.active()
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
        context['report_by_program_block'] = compact_queryset_block(
            request, queryset, prefix='report_by_program', page_size=per_page
        )

    if fragment in {'', 'report_by_discipline'}:
        queryset = (
            Discipline.objects.filter(id__in=discipline_ids)
            .annotate(
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
        context['report_by_discipline_block'] = compact_queryset_block(
            request, queryset, prefix='report_by_discipline', page_size=per_page
        )

    if fragment in {'', 'competence_coverage'}:
        queryset = Competence.objects.filter(
            educational_program__is_deleted=False,
            educational_program_id__in=program_ids,
        )
        if educational_program:
            queryset = queryset.filter(educational_program=educational_program)
        if competence:
            queryset = queryset.filter(pk=competence.pk)
        queryset = queryset.values(
            'id',
            'code',
            'name',
            'competence_type__name',
            'educational_program__program_profile__code',
        ).order_by('educational_program__program_profile__code', 'code')
        block = compact_queryset_block(request, queryset, prefix='competence_coverage', page_size=per_page)
        rows = list(block['items'])
        counts = count_items_by_competence(filtered_item_ids, [row['id'] for row in rows])
        for row in rows:
            row['items_count'] = counts.get(row['id'], 0)
        block['items'] = rows
        context['competence_coverage_block'] = block

    if fragment in {'', 'discipline_competence'}:
        queryset = DisciplineCompetence.objects.filter(
            program_discipline__educational_program__is_deleted=False,
            program_discipline_id__in=program_discipline_ids,
        )
        if educational_program:
            queryset = queryset.filter(program_discipline__educational_program=educational_program)
        if discipline:
            queryset = queryset.filter(program_discipline__discipline=discipline)
        if competence:
            queryset = queryset.filter(competence=competence)
        queryset = queryset.values(
            'program_discipline_id',
            'program_discipline__discipline_code',
            'program_discipline__discipline__name',
            'competence_id',
            'competence__code',
            'competence__name',
        ).order_by(
            'program_discipline__discipline_code',
            'program_discipline__discipline__name',
            'competence__code',
        )
        block = compact_queryset_block(request, queryset, prefix='discipline_competence', page_size=per_page)
        rows = list(block['items'])
        counts = count_items_by_program_discipline_competence(
            filtered_item_ids,
            [(row['program_discipline_id'], row['competence_id']) for row in rows],
        )
        for row in rows:
            code = row.get('program_discipline__discipline_code')
            name = row['program_discipline__discipline__name']
            row['discipline_label'] = f'{code} — {name}' if code else name
            row['items_count'] = counts.get((row['program_discipline_id'], row['competence_id']), 0)
        block['items'] = rows
        context['discipline_competence_block'] = block

    return context
