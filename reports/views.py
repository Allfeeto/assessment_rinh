from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from assessment.models import AssessmentItemType
from competencies.models import Competence, DisciplineCompetence
from core.models import EducationalProgram
from disciplines.models import Discipline, ProgramDiscipline


class DisciplineCompetenceCountReportView(View):
    def get(self, request, *args, **kwargs):
        queryset = DisciplineCompetence.objects.select_related(
            'program_discipline__discipline',
            'program_discipline__educational_program',
            'competence',
        )

        program_id = request.GET.get('program')
        if program_id:
            queryset = queryset.filter(program_discipline__educational_program_id=program_id)

        discipline_id = request.GET.get('discipline')
        if discipline_id:
            queryset = queryset.filter(program_discipline__discipline_id=discipline_id)

        rows = list(
            queryset.values(
                'program_discipline__discipline_id',
                'program_discipline__discipline__name',
                'competence_id',
                'competence__code',
                'competence__name',
            )
            .annotate(
                links_count=Count('id'),
                assessment_items_count=Count(
                    'competence__assessment_item_links__assessment_item',
                    filter=Q(
                        competence__assessment_item_links__assessment_item__program_discipline=F(
                            'program_discipline'
                        )
                    ),
                    distinct=True,
                ),
            )
            .order_by('program_discipline__discipline__name', 'competence__code')
        )

        return JsonResponse({'results': rows, 'count': len(rows)})


class ProgramCompetenceCoverageReportView(View):
    def get(self, request, *args, **kwargs):
        queryset = Competence.objects.select_related('educational_program', 'competence_type')

        program_id = request.GET.get('program')
        if program_id:
            queryset = queryset.filter(educational_program_id=program_id)

        queryset = queryset.annotate(
            disciplines_count=Count('discipline_competences__program_discipline', distinct=True),
            assessment_items_count=Count(
                'assessment_item_links__assessment_item',
                distinct=True,
            ),
        ).order_by('educational_program__code', 'code')

        totals = dict(
            ProgramDiscipline.objects.values('educational_program_id')
            .annotate(total=Count('id'))
            .values_list('educational_program_id', 'total')
        )

        data = []
        for competence in queryset:
            total_disciplines = totals.get(competence.educational_program_id, 0)
            coverage_percent = 0
            if total_disciplines:
                coverage_percent = round((competence.disciplines_count / total_disciplines) * 100, 2)

            data.append(
                {
                    'program_id': competence.educational_program_id,
                    'program_code': competence.educational_program.code,
                    'competence_id': competence.id,
                    'competence_code': competence.code,
                    'competence_name': competence.name,
                    'competence_type': competence.competence_type.name,
                    'disciplines_count': competence.disciplines_count,
                    'total_disciplines': total_disciplines,
                    'coverage_percent': coverage_percent,
                    'assessment_items_count': competence.assessment_items_count,
                }
            )

        return JsonResponse({'results': data, 'count': len(data)})


class AssessmentByTypeReportView(View):
    def get(self, request, *args, **kwargs):
        filters = Q()

        program_id = request.GET.get('program')
        if program_id:
            filters &= Q(assessment_items__program_discipline__educational_program_id=program_id)

        discipline_id = request.GET.get('discipline')
        if discipline_id:
            filters &= Q(assessment_items__program_discipline__discipline_id=discipline_id)

        competence_id = request.GET.get('competence')
        if competence_id:
            filters &= Q(assessment_items__competence_links__competence_id=competence_id)

        rows = list(
            AssessmentItemType.objects.annotate(
                items_count=Count('assessment_items', filter=filters, distinct=True)
            )
            .values('id', 'name', 'items_count')
            .order_by('name')
        )

        return JsonResponse({'results': rows, 'count': len(rows)})


class ReportsPageView(TemplateView):
    template_name = 'reports/report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        program_id = self.request.GET.get('program')
        discipline_id = self.request.GET.get('discipline')
        competence_id = self.request.GET.get('competence')

        discipline_competence_queryset = DisciplineCompetence.objects.select_related(
            'program_discipline__discipline',
            'program_discipline__educational_program',
            'competence',
        )
        if program_id:
            discipline_competence_queryset = discipline_competence_queryset.filter(
                program_discipline__educational_program_id=program_id
            )
        if discipline_id:
            discipline_competence_queryset = discipline_competence_queryset.filter(
                program_discipline__discipline_id=discipline_id
            )

        report_discipline_competence = list(
            discipline_competence_queryset.values(
                'program_discipline__discipline__name',
                'competence__code',
                'competence__name',
            )
            .annotate(links_count=Count('id'))
            .order_by('program_discipline__discipline__name', 'competence__code')
        )

        competence_coverage_queryset = Competence.objects.select_related(
            'educational_program',
            'competence_type',
        )
        if program_id:
            competence_coverage_queryset = competence_coverage_queryset.filter(
                educational_program_id=program_id
            )

        competence_coverage_queryset = competence_coverage_queryset.annotate(
            disciplines_count=Count('discipline_competences__program_discipline', distinct=True),
            assessment_items_count=Count(
                'assessment_item_links__assessment_item',
                distinct=True,
            ),
        ).order_by('educational_program__code', 'code')

        totals = dict(
            ProgramDiscipline.objects.values('educational_program_id')
            .annotate(total=Count('id'))
            .values_list('educational_program_id', 'total')
        )

        report_competence_coverage = []
        for competence in competence_coverage_queryset:
            total_disciplines = totals.get(competence.educational_program_id, 0)
            coverage_percent = (
                round((competence.disciplines_count / total_disciplines) * 100, 2)
                if total_disciplines
                else 0
            )
            report_competence_coverage.append(
                {
                    'program_code': competence.educational_program.code,
                    'competence_code': competence.code,
                    'competence_name': competence.name,
                    'competence_type': competence.competence_type.name,
                    'disciplines_count': competence.disciplines_count,
                    'coverage_percent': coverage_percent,
                    'assessment_items_count': competence.assessment_items_count,
                }
            )

        assessment_filters = Q()
        if program_id:
            assessment_filters &= Q(
                assessment_items__program_discipline__educational_program_id=program_id
            )
        if discipline_id:
            assessment_filters &= Q(
                assessment_items__program_discipline__discipline_id=discipline_id
            )
        if competence_id:
            assessment_filters &= Q(assessment_items__competence_links__competence_id=competence_id)

        report_assessment_by_type = list(
            AssessmentItemType.objects.annotate(
                items_count=Count('assessment_items', filter=assessment_filters, distinct=True)
            )
            .values('name', 'items_count')
            .order_by('name')
        )

        context['programs'] = EducationalProgram.objects.order_by('code')
        context['disciplines'] = Discipline.objects.order_by('name')
        context['competences'] = Competence.objects.order_by('code')
        context['selected_program'] = program_id or ''
        context['selected_discipline'] = discipline_id or ''
        context['selected_competence'] = competence_id or ''
        context['report_discipline_competence'] = report_discipline_competence
        context['report_competence_coverage'] = report_competence_coverage
        context['report_assessment_by_type'] = report_assessment_by_type
        return context
