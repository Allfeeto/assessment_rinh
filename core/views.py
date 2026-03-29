from django.http import JsonResponse
from django.views.generic import ListView, TemplateView

from assessment.models import AssessmentItem
from competencies.models import Competence
from disciplines.models import Discipline
from .models import EducationalProgram


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'programs': EducationalProgram.objects.count(),
            'disciplines': Discipline.objects.count(),
            'competences': Competence.objects.count(),
            'assessment_items': AssessmentItem.objects.count(),
        }
        return context


class EducationalProgramListView(ListView):
    model = EducationalProgram

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related('education_level', 'department')
            .order_by('code')
        )

        education_level_id = self.request.GET.get('education_level')
        if education_level_id:
            queryset = queryset.filter(education_level_id=education_level_id)

        department_id = self.request.GET.get('department')
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        return queryset

    def render_to_response(self, context, **response_kwargs):
        data = [
            {
                'id': program.id,
                'code': program.code,
                'name': program.name,
                'education_level': {
                    'id': program.education_level_id,
                    'name': program.education_level.name,
                },
                'department': {
                    'id': program.department_id,
                    'short_name': program.department.short_name,
                },
            }
            for program in context['object_list']
        ]
        return JsonResponse({'results': data, 'count': len(data)})
