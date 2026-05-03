from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from assessment.access import program_discipline_queryset_for_user
from assessment.models import AssessmentItem
from core.permissions import is_domain_manager
from programs.models import EducationalProgram

from core.view_helpers import (
    PER_PAGE_CHOICES,
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
    StaffOrModelPermissionRequiredMixin,
    get_per_page,
)

from .forms import DisciplineForm, ProgramDisciplineForm, ProgramDisciplineManageForm
from .models import Discipline, ProgramDiscipline
from competencies.models import DisciplineCompetence


class ProgramDisciplineManagerView(StaffOrModelPermissionRequiredMixin, View):
    model = ProgramDiscipline
    permission_action = 'change'
    template_name = 'disciplines/manage_program_disciplines.html'

    @staticmethod
    def _get_selected_program_id(request, form=None):
        if form is not None and form.is_bound:
            return (form.data.get('educational_program') or '').strip()
        return (request.GET.get('educational_program') or '').strip()

    @staticmethod
    def _get_selected_discipline_id(request):
        return (request.GET.get('discipline') or '').strip()

    def _build_context(self, request, form):
        selected_program_id = self._get_selected_program_id(request, form=form)
        selected_discipline_id = self._get_selected_discipline_id(request)
        per_page = get_per_page(request)

        selected_program = None
        educational_program_options = EducationalProgram.objects.none()
        existing_program_disciplines_qs = ProgramDiscipline.objects.none()
        discipline_filter_options = []
        selected_program_discipline = None
        discipline_competence_links = DisciplineCompetence.objects.none()
        if selected_program_id:
            selected_program = (
                EducationalProgram.objects.select_related('program_profile', 'department')
                .filter(pk=selected_program_id, is_deleted=False)
                .first()
            )
            if selected_program:
                educational_program_options = EducationalProgram.objects.filter(
                    pk=selected_program.pk,
                    is_deleted=False,
                )

            existing_program_disciplines_qs = ProgramDiscipline.objects.select_related('discipline').filter(
                educational_program_id=selected_program_id,
                educational_program__is_deleted=False,
            ).order_by('discipline__name')

            discipline_filter_options = list(
                existing_program_disciplines_qs.values('discipline_id', 'discipline__name').distinct()
            )
            valid_discipline_ids = {str(option['discipline_id']) for option in discipline_filter_options}
            if selected_discipline_id and selected_discipline_id not in valid_discipline_ids:
                selected_discipline_id = ''

            if selected_discipline_id:
                existing_program_disciplines_qs = existing_program_disciplines_qs.filter(
                    discipline_id=selected_discipline_id
                )
                selected_program_discipline = existing_program_disciplines_qs.first()
                if selected_program_discipline:
                    discipline_competence_links = DisciplineCompetence.objects.select_related(
                        'competence__competence_type'
                    ).filter(
                        program_discipline=selected_program_discipline
                    ).order_by('competence__code')

        program_disciplines_paginator = Paginator(existing_program_disciplines_qs, per_page)
        pd_page_obj = program_disciplines_paginator.get_page(request.GET.get('pd_page') or 1)

        params = request.GET.copy()
        params.pop('pd_page', None)

        return {
            'form': form,
            'selected_program': selected_program,
            'educational_program_options': educational_program_options,
            'selected_program_id': selected_program_id,
            'selected_discipline_id': selected_discipline_id,
            'discipline_filter_options': discipline_filter_options,
            'selected_program_discipline': selected_program_discipline,
            'discipline_competence_links': discipline_competence_links,
            'existing_program_disciplines': pd_page_obj.object_list,
            'pd_page_obj': pd_page_obj,
            'pd_query_params': params.urlencode(),
            'per_page_choices': PER_PAGE_CHOICES,
            'selected_per_page': per_page,
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


class DisciplinesDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'disciplines/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        educational_program_id = self.request.GET.get('educational_program', '').strip()
        search = self.request.GET.get('q', '').strip()
        per_page = get_per_page(self.request)
        can_manage_disciplines = is_domain_manager(self.request.user)
        program_discipline_scope = program_discipline_queryset_for_user(self.request.user)

        # Считаем агрегаты через Subquery, чтобы избежать инфляции
        # из-за пересекающихся JOIN’ов при нескольких Count(distinct=True).
        discipline_programs_count = (
            program_discipline_scope.filter(
                discipline=OuterRef('pk'),
                educational_program__is_deleted=False,
            )
            .order_by()
            .values('discipline')
            .annotate(total=Count('id'))
            .values('total')
        )
        discipline_items_count = (
            AssessmentItem.objects.filter(
                program_discipline__discipline=OuterRef('pk'),
                program_discipline__in=program_discipline_scope,
                program_discipline__educational_program__is_deleted=False,
            )
            .order_by()
            .values('program_discipline__discipline')
            .annotate(total=Count('id'))
            .values('total')
        )

        disciplines_base_qs = Discipline.objects.all()
        if not can_manage_disciplines:
            disciplines_base_qs = disciplines_base_qs.filter(
                program_disciplines__in=program_discipline_scope,
            ).distinct()

        disciplines_qs = disciplines_base_qs.annotate(
            programs_count=Coalesce(
                Subquery(discipline_programs_count, output_field=IntegerField()),
                0,
            ),
            items_count=Coalesce(
                Subquery(discipline_items_count, output_field=IntegerField()),
                0,
            ),
        ).order_by('name')

        if search:
            disciplines_qs = disciplines_qs.filter(name__icontains=search)

        program_discipline_competences_count = (
            DisciplineCompetence.objects.filter(
                program_discipline=OuterRef('pk'),
                program_discipline__educational_program__is_deleted=False,
            )
            .order_by()
            .values('program_discipline')
            .annotate(total=Count('id'))
            .values('total')
        )
        program_discipline_items_count = (
            AssessmentItem.objects.filter(
                program_discipline=OuterRef('pk'),
                program_discipline__educational_program__is_deleted=False,
            )
            .order_by()
            .values('program_discipline')
            .annotate(total=Count('id'))
            .values('total')
        )

        program_disciplines_qs = program_discipline_scope.select_related(
            'educational_program__program_profile',
            'educational_program__department',
            'discipline',
        ).annotate(
            competences_count=Coalesce(
                Subquery(program_discipline_competences_count, output_field=IntegerField()),
                0,
            ),
            items_count=Coalesce(
                Subquery(program_discipline_items_count, output_field=IntegerField()),
                0,
            ),
        ).order_by(
            'educational_program__program_profile__code',
            'educational_program__admission_year',
            'discipline__name',
        )

        if educational_program_id:
            program_disciplines_qs = program_disciplines_qs.filter(educational_program_id=educational_program_id)

        disciplines_paginator = Paginator(disciplines_qs, per_page)
        d_page_obj = disciplines_paginator.get_page(self.request.GET.get('d_page') or 1)

        program_disciplines_paginator = Paginator(program_disciplines_qs, per_page)
        pd_page_obj = program_disciplines_paginator.get_page(self.request.GET.get('pd_page') or 1)

        selected_program = (
            EducationalProgram.objects.select_related('program_profile', 'department')
            .filter(
                pk=educational_program_id,
                is_deleted=False,
                program_disciplines__in=program_discipline_scope,
            )
            .distinct()
            .first()
            if educational_program_id
            else None
        )
        educational_program_options = (
            EducationalProgram.objects.filter(pk=selected_program.pk, is_deleted=False)
            if selected_program
            else EducationalProgram.objects.none()
        )

        params = self.request.GET.copy()
        d_params = params.copy()
        d_params.pop('d_page', None)
        pd_params = params.copy()
        pd_params.pop('pd_page', None)

        context['educational_programs'] = educational_program_options
        context['selected_program'] = educational_program_id
        context['search_query'] = search
        context['disciplines'] = d_page_obj.object_list
        context['program_disciplines'] = pd_page_obj.object_list
        context['d_page_obj'] = d_page_obj
        context['pd_page_obj'] = pd_page_obj
        context['d_query_params'] = d_params.urlencode()
        context['pd_query_params'] = pd_params.urlencode()
        context['per_page_choices'] = PER_PAGE_CHOICES
        context['selected_per_page'] = per_page
        context['can_manage_disciplines'] = can_manage_disciplines
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

    def get_queryset(self):
        return super().get_queryset().filter(educational_program__is_deleted=False)


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

    def get_queryset(self):
        return super().get_queryset().filter(educational_program__is_deleted=False)


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

    def get_queryset(self):
        return super().get_queryset().filter(educational_program__is_deleted=False)


class ProgramDisciplineDeleteView(NamedDeleteView):
    model = ProgramDiscipline
    title = 'Удалить дисциплину учебного плана'
    list_url_name = 'disciplines_program_discipline_list'

    def get_queryset(self):
        return super().get_queryset().filter(educational_program__is_deleted=False)


@login_required
def program_discipline_by_program(request):
    educational_program_id = request.GET.get('educational_program_id')
    queryset = program_discipline_queryset_for_user(request.user).select_related(
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
