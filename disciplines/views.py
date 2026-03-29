from django.http import JsonResponse
from django.views.generic import ListView

from .models import ProgramDiscipline


class ProgramDisciplineListView(ListView):
    model = ProgramDiscipline

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related('educational_program', 'discipline')
            .order_by('educational_program__code', 'discipline__name')
        )

        program_id = self.request.GET.get('program')
        if program_id:
            queryset = queryset.filter(educational_program_id=program_id)

        discipline_id = self.request.GET.get('discipline')
        if discipline_id:
            queryset = queryset.filter(discipline_id=discipline_id)

        return queryset

    def render_to_response(self, context, **response_kwargs):
        data = [
            {
                'id': program_discipline.id,
                'program': {
                    'id': program_discipline.educational_program_id,
                    'code': program_discipline.educational_program.code,
                    'name': program_discipline.educational_program.name,
                },
                'discipline': {
                    'id': program_discipline.discipline_id,
                    'name': program_discipline.discipline.name,
                },
            }
            for program_discipline in context['object_list']
        ]
        return JsonResponse({'results': data, 'count': len(data)})