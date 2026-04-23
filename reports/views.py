from django.db.models import Count, Q
from django.views.generic import TemplateView

from assessment.models import AssessmentItem
from assessment.services import get_item_type_ui_name
from competencies.models import Competence, DisciplineCompetence
from core.models import AssessmentItemType
from disciplines.models import Discipline
from programs.models import EducationalProgram

from .forms import ReportFilterForm


class ReportsDashboardView(TemplateView):
    template_name = 'reports/report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = ReportFilterForm(self.request.GET or None)
        form.is_valid()
        cleaned = form.cleaned_data if form.is_valid() else {}

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
        filtered_item_ids = list(assessment_items.values_list('id', flat=True))

        report_by_type = list(
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
        for row in report_by_type:
            row['ui_name'] = get_item_type_ui_name(row['name'])

        report_by_program = list(
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

        report_by_discipline = list(
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

        competence_coverage_qs = Competence.objects.select_related(
            'educational_program__program_profile',
            'competence_type',
        )
        if educational_program:
            competence_coverage_qs = competence_coverage_qs.filter(educational_program=educational_program)
        if competence:
            competence_coverage_qs = competence_coverage_qs.filter(pk=competence.pk)

        competence_coverage = list(
            competence_coverage_qs.annotate(
                items_count=Count('id')
            )
            .values(
                'id',
                'code',
                'name',
                'competence_type__name',
                'educational_program__program_profile__code',
                'items_count',
            )
            .order_by('educational_program__program_profile__code', 'code')
        )
        for row in competence_coverage:
            row['items_count'] = (
                AssessmentItem.objects.filter(id__in=filtered_item_ids)
                .filter(
                    Q(competence_id=row['id']) | Q(competence_links__competence_id=row['id'])
                )
                .distinct()
                .count()
            )

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

        discipline_competence_report = list(
            discipline_competence_qs.values(
                'program_discipline_id',
                'program_discipline__discipline__name',
                'competence_id',
                'competence__code',
                'competence__name',
            )
            .order_by('program_discipline__discipline__name', 'competence__code')
        )
        for row in discipline_competence_report:
            row['items_count'] = (
                AssessmentItem.objects.filter(
                    id__in=filtered_item_ids,
                    program_discipline_id=row['program_discipline_id'],
                )
                .filter(
                    Q(competence_id=row['competence_id'])
                    | Q(competence_links__competence_id=row['competence_id'])
                )
                .distinct()
                .count()
            )

        context['form'] = form
        context['assessment_items_count'] = assessment_items.count()
        context['report_by_type'] = report_by_type
        context['report_by_program'] = report_by_program
        context['report_by_discipline'] = report_by_discipline
        context['competence_coverage'] = competence_coverage
        context['discipline_competence_report'] = discipline_competence_report
        return context
