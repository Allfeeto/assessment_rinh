from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from programs.models import EducationalProgram

from core.view_helpers import (
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
)

from .forms import DisciplineForm, ProgramDisciplineForm, ProgramDisciplineManageForm
from .models import Discipline, ProgramDiscipline


class ProgramDisciplineManagerView(View):
    template_name = 'disciplines/manage_program_disciplines.html'

    @staticmethod
    def _get_selected_program_id(request, form=None):
        if form is not None and form.is_bound:
            return (form.data.get('educational_program') or '').strip()
        return (request.GET.get('educational_program') or '').strip()

    def _build_context(self, request, form):
        selected_program_id = self._get_selected_program_id(request, form=form)

        selected_program = None
        existing_program_disciplines = ProgramDiscipline.objects.none()
        if selected_program_id:
            selected_program = (
                EducationalProgram.objects.select_related('program_profile', 'department')
                .filter(pk=selected_program_id)
                .first()
            )
            existing_program_disciplines = ProgramDiscipline.objects.select_related('discipline').filter(
                educational_program_id=selected_program_id
            ).order_by('discipline__name')

        return {
            'form': form,
            'selected_program': selected_program,
            'existing_program_disciplines': existing_program_disciplines,
        }

    def get(self, request, *args, **kwargs):
        selected_program_id = self._get_selected_program_id(request)
        initial = {'educational_program': selected_program_id} if selected_program_id else None
        form = ProgramDisciplineManageForm(initial=initial)
        return render(request, self.template_name, self._build_context(request, form))

    def post(self, request, *args, **kwargs):
        form = ProgramDisciplineManageForm(request.POST)

        if form.is_valid():
            educational_program = form.cleaned_data['educational_program']
            discipline = form.cleaned_data['discipline']

            try:
                ProgramDiscipline.objects.create(
                    educational_program=educational_program,
                    discipline=discipline,
                )
            except IntegrityError:
                form.add_error('discipline', 'Эта дисциплина уже добавлена в выбранный учебный план.')
            else:
                messages.success(request, 'Дисциплина успешно добавлена в учебный план.')
                return redirect(
                    f"{reverse('disciplines_root')}?educational_program={educational_program.id}"
                )

        return render(request, self.template_name, self._build_context(request, form))


class DisciplinesDashboardView(TemplateView):
    template_name = 'disciplines/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        educational_program_id = self.request.GET.get('educational_program', '').strip()
        search = self.request.GET.get('q', '').strip()

        disciplines = Discipline.objects.annotate(
            programs_count=Count('program_disciplines', distinct=True),
            items_count=Count('program_disciplines__assessment_items', distinct=True),
        ).order_by('name')

        if search:
            disciplines = disciplines.filter(name__icontains=search)

        program_disciplines = ProgramDiscipline.objects.select_related(
            'educational_program__program_profile',
            'educational_program__department',
            'discipline',
        ).annotate(
            competences_count=Count('discipline_competences', distinct=True),
            items_count=Count('assessment_items', distinct=True),
        ).order_by(
            'educational_program__program_profile__code',
            'educational_program__admission_year',
            'discipline__name',
        )

        if educational_program_id:
            program_disciplines = program_disciplines.filter(educational_program_id=educational_program_id)

        context['educational_programs'] = EducationalProgram.objects.select_related(
            'program_profile',
            'department',
        ).order_by('program_profile__code', 'admission_year')
        context['selected_program'] = educational_program_id
        context['search_query'] = search
        context['disciplines'] = disciplines
        context['program_disciplines'] = program_disciplines
        return context


class DisciplineListView(NamedListView):
    model = Discipline
    title = 'Справочник дисциплин'
    search_fields = ('name',)
    list_columns = (('ID', 'id'), ('Наименование', 'name'))
    create_url_name = 'disciplines_discipline_create'
    detail_url_name = 'disciplines_discipline_detail'
    update_url_name = 'disciplines_discipline_update'
    delete_url_name = 'disciplines_discipline_delete'


class DisciplineDetailView(NamedDetailView):
    model = Discipline
    title = 'Карточка дисциплины'
    list_url_name = 'disciplines_discipline_list'
    update_url_name = 'disciplines_discipline_update'
    delete_url_name = 'disciplines_discipline_delete'
    detail_fields = (('ID', 'id'), ('Наименование', 'name'))


class DisciplineCreateView(NamedCreateView):
    model = Discipline
    form_class = DisciplineForm
    title = 'Создать дисциплину'
    list_url_name = 'disciplines_discipline_list'


class DisciplineUpdateView(NamedUpdateView):
    model = Discipline
    form_class = DisciplineForm
    title = 'Редактировать дисциплину'
    list_url_name = 'disciplines_discipline_list'


class DisciplineDeleteView(NamedDeleteView):
    model = Discipline
    title = 'Удалить дисциплину'
    list_url_name = 'disciplines_discipline_list'


class ProgramDisciplineListView(NamedListView):
    model = ProgramDiscipline
    title = 'Дисциплины учебных планов'
    search_fields = (
        'discipline__name',
        'educational_program__program_profile__code',
        'educational_program__program_profile__name',
    )
    list_columns = (
        ('ID', 'id'),
        ('Программа', 'educational_program'),
        ('Дисциплина', 'discipline.name'),
    )
    create_url_name = 'disciplines_program_discipline_create'
    detail_url_name = 'disciplines_program_discipline_detail'
    update_url_name = 'disciplines_program_discipline_update'
    delete_url_name = 'disciplines_program_discipline_delete'


class ProgramDisciplineDetailView(NamedDetailView):
    model = ProgramDiscipline
    title = 'Карточка дисциплины учебного плана'
    list_url_name = 'disciplines_program_discipline_list'
    update_url_name = 'disciplines_program_discipline_update'
    delete_url_name = 'disciplines_program_discipline_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Программа', 'educational_program'),
        ('Дисциплина', 'discipline.name'),
    )


class ProgramDisciplineCreateView(NamedCreateView):
    model = ProgramDiscipline
    form_class = ProgramDisciplineForm
    title = 'Создать дисциплину учебного плана'
    list_url_name = 'disciplines_program_discipline_list'


class ProgramDisciplineUpdateView(NamedUpdateView):
    model = ProgramDiscipline
    form_class = ProgramDisciplineForm
    title = 'Редактировать дисциплину учебного плана'
    list_url_name = 'disciplines_program_discipline_list'


class ProgramDisciplineDeleteView(NamedDeleteView):
    model = ProgramDiscipline
    title = 'Удалить дисциплину учебного плана'
    list_url_name = 'disciplines_program_discipline_list'


def program_discipline_by_program(request):
    educational_program_id = request.GET.get('educational_program_id')
    queryset = ProgramDiscipline.objects.select_related(
        'educational_program__program_profile',
        'discipline',
    ).order_by(
        'educational_program__program_profile__code',
        'educational_program__admission_year',
        'discipline__name',
    )
    if educational_program_id:
        queryset = queryset.filter(educational_program_id=educational_program_id)

    data = [
        {
            'id': obj.id,
            'label': f'{obj.educational_program} | {obj.discipline.name}',
            'discipline_id': obj.discipline_id,
        }
        for obj in queryset
    ]
    return JsonResponse({'results': data})
