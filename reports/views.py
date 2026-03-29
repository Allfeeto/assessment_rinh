from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.views import View

from assessment.models import AssessmentItemType
from competencies.models import Competence, DisciplineCompetence
from disciplines.models import ProgramDiscipline


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