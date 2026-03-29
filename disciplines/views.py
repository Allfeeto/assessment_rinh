from django.http import JsonResponse
from django.db.models import Count
from django.views.generic import DetailView, ListView

from .models import Discipline, ProgramDiscipline


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


class DisciplinePageListView(ListView):
    model = Discipline
    template_name = 'disciplines/list.html'
    context_object_name = 'disciplines'
    paginate_by = 15

    def get_queryset(self):
        queryset = (
            Discipline.objects.annotate(
                programs_count=Count('program_disciplines', distinct=True),
                items_count=Count('program_disciplines__assessment_items', distinct=True),
            )
            .order_by('name')
        )

        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_params'] = params.urlencode()
        return context


class DisciplinePageDetailView(DetailView):
    model = Discipline
    template_name = 'disciplines/detail.html'
    context_object_name = 'discipline'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['program_disciplines'] = (
            ProgramDiscipline.objects.filter(discipline=self.object)
            .select_related('educational_program')
            .annotate(
                items_count=Count('assessment_items', distinct=True),
                competences_count=Count('discipline_competences', distinct=True),
            )
            .order_by('educational_program__code')
        )
        return context
