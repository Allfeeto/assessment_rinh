from django.http import JsonResponse
from django.views.generic import ListView

from .models import Competence


class CompetenceListView(ListView):
    model = Competence

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related('educational_program', 'competence_type')
            .order_by('code')
        )

        program_id = self.request.GET.get('program')
        if program_id:
            queryset = queryset.filter(educational_program_id=program_id)

        competence_type_id = self.request.GET.get('competence_type')
        if competence_type_id:
            queryset = queryset.filter(competence_type_id=competence_type_id)

        return queryset

    def render_to_response(self, context, **response_kwargs):
        data = [
            {
                'id': competence.id,
                'code': competence.code,
                'name': competence.name,
                'competence_type': competence.competence_type.name,
                'program_id': competence.educational_program_id,
            }
            for competence in context['object_list']
        ]
        return JsonResponse({'results': data, 'count': len(data)})