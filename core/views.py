from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth import get_user_model
import re

from assessment.models import AssessmentItem
from competencies.models import Competence, DisciplineCompetence
from disciplines.models import Discipline, ProgramDiscipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from teachers.models import Department, Teacher

from .forms import (
    AcademicDegreeForm,
    AcademicTitleForm,
    AssessmentItemTypeForm,
    CompetenceTypeForm,
    EducationLevelForm,
)
from .models import AcademicDegree, AcademicTitle, AssessmentItemType, CompetenceType, EducationLevel
from .view_helpers import (
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
)


LOOKUP_STOP_WORDS = {'набор', 'года', 'год', 'программа', 'профиль'}


def _tokenize_lookup_query(query: str) -> list[str]:
    if not query:
        return []
    tokens = re.split(r'[\s|,;:()«»"\'/\\\-]+', query)
    cleaned = []
    for token in tokens:
        value = token.strip().lower()
        if not value or value in LOOKUP_STOP_WORDS:
            continue
        if value.isdigit() and len(value) < 4:
            continue
        cleaned.append(value)
    return cleaned


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'education_levels': EducationLevel.objects.count(),
            'departments': Department.objects.count(),
            'teachers': Teacher.objects.count(),
            'training_directions': TrainingDirection.objects.count(),
            'program_profiles': ProgramProfile.objects.count(),
            'educational_programs': EducationalProgram.objects.count(),
            'programs': EducationalProgram.objects.count(),
            'disciplines': Discipline.objects.count(),
            'competences': Competence.objects.count(),
            'assessment_items': AssessmentItem.objects.count(),
        }
        return context


class EducationLevelListView(NamedListView):
    model = EducationLevel
    title = 'Справочник уровней образования'
    search_fields = ('name',)
    list_columns = (('ID', 'id'), ('Наименование', 'name'))
    create_url_name = 'core_education_level_create'
    detail_url_name = 'core_education_level_detail'
    update_url_name = 'core_education_level_update'
    delete_url_name = 'core_education_level_delete'


class EducationLevelDetailView(NamedDetailView):
    model = EducationLevel
    title = 'Карточка уровня образования'
    list_url_name = 'core_education_level_list'
    update_url_name = 'core_education_level_update'
    delete_url_name = 'core_education_level_delete'
    detail_fields = (('ID', 'id'), ('Наименование', 'name'))


class EducationLevelCreateView(NamedCreateView):
    model = EducationLevel
    form_class = EducationLevelForm
    title = 'Создать уровень образования'
    list_url_name = 'core_education_level_list'


class EducationLevelUpdateView(NamedUpdateView):
    model = EducationLevel
    form_class = EducationLevelForm
    title = 'Редактировать уровень образования'
    list_url_name = 'core_education_level_list'


class EducationLevelDeleteView(NamedDeleteView):
    model = EducationLevel
    title = 'Удалить уровень образования'
    list_url_name = 'core_education_level_list'


class CompetenceTypeListView(NamedListView):
    model = CompetenceType
    title = 'Справочник типов компетенций'
    search_fields = ('name',)
    list_columns = (('ID', 'id'), ('Наименование', 'name'))
    create_url_name = 'core_competence_type_create'
    detail_url_name = 'core_competence_type_detail'
    update_url_name = 'core_competence_type_update'
    delete_url_name = 'core_competence_type_delete'


class CompetenceTypeDetailView(NamedDetailView):
    model = CompetenceType
    title = 'Карточка типа компетенции'
    list_url_name = 'core_competence_type_list'
    update_url_name = 'core_competence_type_update'
    delete_url_name = 'core_competence_type_delete'
    detail_fields = (('ID', 'id'), ('Наименование', 'name'))


class CompetenceTypeCreateView(NamedCreateView):
    model = CompetenceType
    form_class = CompetenceTypeForm
    title = 'Создать тип компетенции'
    list_url_name = 'core_competence_type_list'


class CompetenceTypeUpdateView(NamedUpdateView):
    model = CompetenceType
    form_class = CompetenceTypeForm
    title = 'Редактировать тип компетенции'
    list_url_name = 'core_competence_type_list'


class CompetenceTypeDeleteView(NamedDeleteView):
    model = CompetenceType
    title = 'Удалить тип компетенции'
    list_url_name = 'core_competence_type_list'


class AssessmentItemTypeListView(NamedListView):
    model = AssessmentItemType
    title = 'Справочник типов заданий'
    search_fields = ('name',)
    list_columns = (('ID', 'id'), ('Наименование', 'name'))
    create_url_name = 'core_assessment_item_type_create'
    detail_url_name = 'core_assessment_item_type_detail'
    update_url_name = 'core_assessment_item_type_update'
    delete_url_name = 'core_assessment_item_type_delete'


class AssessmentItemTypeDetailView(NamedDetailView):
    model = AssessmentItemType
    title = 'Карточка типа задания'
    list_url_name = 'core_assessment_item_type_list'
    update_url_name = 'core_assessment_item_type_update'
    delete_url_name = 'core_assessment_item_type_delete'
    detail_fields = (('ID', 'id'), ('Наименование', 'name'))


class AssessmentItemTypeCreateView(NamedCreateView):
    model = AssessmentItemType
    form_class = AssessmentItemTypeForm
    title = 'Создать тип задания'
    list_url_name = 'core_assessment_item_type_list'


class AssessmentItemTypeUpdateView(NamedUpdateView):
    model = AssessmentItemType
    form_class = AssessmentItemTypeForm
    title = 'Редактировать тип задания'
    list_url_name = 'core_assessment_item_type_list'


class AssessmentItemTypeDeleteView(NamedDeleteView):
    model = AssessmentItemType
    title = 'Удалить тип задания'
    list_url_name = 'core_assessment_item_type_list'


class AcademicDegreeListView(NamedListView):
    model = AcademicDegree
    title = 'Справочник учёных степеней'
    search_fields = ('name',)
    list_columns = (('ID', 'id'), ('Наименование', 'name'))
    create_url_name = 'core_academic_degree_create'
    detail_url_name = 'core_academic_degree_detail'
    update_url_name = 'core_academic_degree_update'
    delete_url_name = 'core_academic_degree_delete'


class AcademicDegreeDetailView(NamedDetailView):
    model = AcademicDegree
    title = 'Карточка учёной степени'
    list_url_name = 'core_academic_degree_list'
    update_url_name = 'core_academic_degree_update'
    delete_url_name = 'core_academic_degree_delete'
    detail_fields = (('ID', 'id'), ('Наименование', 'name'))


class AcademicDegreeCreateView(NamedCreateView):
    model = AcademicDegree
    form_class = AcademicDegreeForm
    title = 'Создать учёную степень'
    list_url_name = 'core_academic_degree_list'


class AcademicDegreeUpdateView(NamedUpdateView):
    model = AcademicDegree
    form_class = AcademicDegreeForm
    title = 'Редактировать учёную степень'
    list_url_name = 'core_academic_degree_list'


class AcademicDegreeDeleteView(NamedDeleteView):
    model = AcademicDegree
    title = 'Удалить учёную степень'
    list_url_name = 'core_academic_degree_list'


class AcademicTitleListView(NamedListView):
    model = AcademicTitle
    title = 'Справочник учёных званий'
    search_fields = ('name',)
    list_columns = (('ID', 'id'), ('Наименование', 'name'))
    create_url_name = 'core_academic_title_create'
    detail_url_name = 'core_academic_title_detail'
    update_url_name = 'core_academic_title_update'
    delete_url_name = 'core_academic_title_delete'


class AcademicTitleDetailView(NamedDetailView):
    model = AcademicTitle
    title = 'Карточка учёного звания'
    list_url_name = 'core_academic_title_list'
    update_url_name = 'core_academic_title_update'
    delete_url_name = 'core_academic_title_delete'
    detail_fields = (('ID', 'id'), ('Наименование', 'name'))


class AcademicTitleCreateView(NamedCreateView):
    model = AcademicTitle
    form_class = AcademicTitleForm
    title = 'Создать учёное звание'
    list_url_name = 'core_academic_title_list'


class AcademicTitleUpdateView(NamedUpdateView):
    model = AcademicTitle
    form_class = AcademicTitleForm
    title = 'Редактировать учёное звание'
    list_url_name = 'core_academic_title_list'


class AcademicTitleDeleteView(NamedDeleteView):
    model = AcademicTitle
    title = 'Удалить учёное звание'
    list_url_name = 'core_academic_title_list'


@login_required
def lookup_options(request):
    kind = (request.GET.get('kind') or '').strip()
    query = (request.GET.get('q') or '').strip()

    try:
        limit = int(request.GET.get('limit', 20))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 50))

    if kind == 'department':
        queryset = Department.objects.order_by('number')
        if query:
            queryset = queryset.filter(
                Q(number__icontains=query)
                | Q(short_name__icontains=query)
                | Q(full_name__icontains=query)
            )
        results = [
            {'id': obj.id, 'label': f'{obj.number} — {obj.short_name}'}
            for obj in queryset[:limit]
        ]
        return JsonResponse({'results': results})

    if kind == 'teacher':
        queryset = Teacher.objects.select_related('department').order_by('full_name')
        department_id = request.GET.get('department_id')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query)
                | Q(department__number__icontains=query)
                | Q(department__short_name__icontains=query)
            )
        results = [
            {'id': obj.id, 'label': f'{obj.full_name} ({obj.department.short_name})'}
            for obj in queryset[:limit]
        ]
        return JsonResponse({'results': results})

    if kind == 'auth_user':
        user_model = get_user_model()
        queryset = user_model.objects.order_by('username')
        selected_user_id = request.GET.get('selected_user_id')
        if selected_user_id and selected_user_id.isdigit():
            queryset = queryset.filter(Q(teacher_profile__isnull=True) | Q(id=int(selected_user_id)))
        else:
            queryset = queryset.filter(teacher_profile__isnull=True)
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
        results = []
        for obj in queryset[:limit]:
            display_name = ' '.join(part for part in [obj.last_name, obj.first_name] if part).strip()
            if display_name:
                label = f'{obj.username} ({display_name})'
            else:
                label = obj.username
            results.append({'id': obj.id, 'label': label})
        return JsonResponse({'results': results})

    if kind == 'training_direction':
        queryset = TrainingDirection.objects.order_by('code')
        education_level_id = request.GET.get('education_level_id')
        if education_level_id:
            queryset = queryset.filter(education_level_id=education_level_id)
        if query:
            queryset = queryset.filter(Q(code__icontains=query) | Q(name__icontains=query))
        results = [
            {'id': obj.id, 'label': f'{obj.code} — {obj.name}'}
            for obj in queryset[:limit]
        ]
        return JsonResponse({'results': results})

    if kind == 'program_profile':
        queryset = ProgramProfile.objects.select_related('training_direction').order_by('code')
        direction_id = request.GET.get('training_direction_id')
        education_level_id = request.GET.get('education_level_id')
        if education_level_id:
            queryset = queryset.filter(training_direction__education_level_id=education_level_id)
        if direction_id:
            queryset = queryset.filter(training_direction_id=direction_id)
        if query:
            queryset = queryset.filter(
                Q(code__icontains=query)
                | Q(name__icontains=query)
                | Q(training_direction__code__icontains=query)
                | Q(training_direction__name__icontains=query)
            )
        results = [
            {
                'id': obj.id,
                'label': f'{obj.code} — {obj.name} ({obj.training_direction.code})',
            }
            for obj in queryset[:limit]
        ]
        return JsonResponse({'results': results})

    if kind == 'educational_program':
        queryset = EducationalProgram.objects.select_related(
            'program_profile__training_direction',
            'department',
        ).order_by('program_profile__code', 'admission_year')
        education_level_id = request.GET.get('education_level_id')
        training_direction_id = request.GET.get('training_direction_id')
        program_profile_id = request.GET.get('program_profile_id')
        discipline_id = request.GET.get('discipline_id')
        competence_id = request.GET.get('competence_id')
        if education_level_id:
            queryset = queryset.filter(
                program_profile__training_direction__education_level_id=education_level_id
            )
        if training_direction_id:
            queryset = queryset.filter(program_profile__training_direction_id=training_direction_id)
        if program_profile_id:
            queryset = queryset.filter(program_profile_id=program_profile_id)
        if discipline_id:
            queryset = queryset.filter(program_disciplines__discipline_id=discipline_id)
        if competence_id:
            queryset = queryset.filter(competences__id=competence_id)
        if query:
            tokens = _tokenize_lookup_query(query)
            if not tokens:
                tokens = [query.strip().lower()]
            for token in tokens:
                token_filter = (
                    Q(program_profile__code__icontains=token)
                    | Q(program_profile__name__icontains=token)
                    | Q(program_profile__training_direction__code__icontains=token)
                    | Q(program_profile__training_direction__name__icontains=token)
                    | Q(department__number__icontains=token)
                    | Q(department__short_name__icontains=token)
                    | Q(department__full_name__icontains=token)
                )
                if token.isdigit() and len(token) == 4:
                    token_filter |= Q(admission_year=int(token))
                queryset = queryset.filter(token_filter)
        results = [{'id': obj.id, 'label': str(obj)} for obj in queryset.distinct()[:limit]]
        return JsonResponse({'results': results})

    if kind == 'discipline':
        queryset = Discipline.objects.order_by('name')
        exclude_program_id = request.GET.get('exclude_program_id')
        education_level_id = request.GET.get('education_level_id')
        training_direction_id = request.GET.get('training_direction_id')
        program_profile_id = request.GET.get('program_profile_id')
        educational_program_id = request.GET.get('educational_program_id')
        competence_id = request.GET.get('competence_id')
        if exclude_program_id:
            linked_ids = ProgramDiscipline.objects.filter(
                educational_program_id=exclude_program_id
            ).values_list('discipline_id', flat=True)
            queryset = queryset.exclude(id__in=linked_ids)
        if (
            education_level_id
            or training_direction_id
            or program_profile_id
            or educational_program_id
            or competence_id
        ):
            linked_program_disciplines = ProgramDiscipline.objects.all()
            if education_level_id:
                linked_program_disciplines = linked_program_disciplines.filter(
                    educational_program__program_profile__training_direction__education_level_id=education_level_id
                )
            if training_direction_id:
                linked_program_disciplines = linked_program_disciplines.filter(
                    educational_program__program_profile__training_direction_id=training_direction_id
                )
            if program_profile_id:
                linked_program_disciplines = linked_program_disciplines.filter(
                    educational_program__program_profile_id=program_profile_id
                )
            if educational_program_id:
                linked_program_disciplines = linked_program_disciplines.filter(
                    educational_program_id=educational_program_id
                )
            if competence_id:
                linked_program_disciplines = linked_program_disciplines.filter(
                    discipline_competences__competence_id=competence_id
                )
            linked_ids = linked_program_disciplines.values_list('discipline_id', flat=True)
            queryset = queryset.filter(id__in=linked_ids)
        if query:
            queryset = queryset.filter(name__icontains=query)
        results = [{'id': obj.id, 'label': obj.name} for obj in queryset.distinct()[:limit]]
        return JsonResponse({'results': results})

    if kind == 'program_discipline':
        queryset = ProgramDiscipline.objects.select_related(
            'educational_program__program_profile',
            'educational_program__department',
            'discipline',
        ).order_by(
            'educational_program__program_profile__code',
            'educational_program__admission_year',
            'discipline__name',
        )
        educational_program_id = request.GET.get('educational_program_id')
        if educational_program_id:
            queryset = queryset.filter(educational_program_id=educational_program_id)
        if query:
            tokens = _tokenize_lookup_query(query)
            if not tokens:
                tokens = [query.strip().lower()]
            for token in tokens:
                token_filter = (
                    Q(discipline__name__icontains=token)
                    | Q(educational_program__program_profile__code__icontains=token)
                    | Q(educational_program__program_profile__name__icontains=token)
                    | Q(educational_program__department__short_name__icontains=token)
                    | Q(educational_program__department__full_name__icontains=token)
                )
                if token.isdigit() and len(token) == 4:
                    token_filter |= Q(educational_program__admission_year=int(token))
                queryset = queryset.filter(token_filter)
        results = [
            {'id': obj.id, 'label': f'{obj.educational_program} | {obj.discipline.name}'}
            for obj in queryset[:limit]
        ]
        return JsonResponse({'results': results})

    if kind == 'competence':
        queryset = Competence.objects.select_related(
            'educational_program__program_profile',
            'competence_type',
        ).order_by('code')

        educational_program_id = request.GET.get('educational_program_id')
        program_discipline_id = request.GET.get('program_discipline_id')
        discipline_id = request.GET.get('discipline_id')
        education_level_id = request.GET.get('education_level_id')
        training_direction_id = request.GET.get('training_direction_id')
        program_profile_id = request.GET.get('program_profile_id')
        linked_only = request.GET.get('linked_only') in {'1', 'true', 'True'}

        if education_level_id:
            queryset = queryset.filter(
                educational_program__program_profile__training_direction__education_level_id=education_level_id
            )
        if training_direction_id:
            queryset = queryset.filter(
                educational_program__program_profile__training_direction_id=training_direction_id
            )
        if program_profile_id:
            queryset = queryset.filter(educational_program__program_profile_id=program_profile_id)

        if program_discipline_id:
            program_id = (
                ProgramDiscipline.objects.filter(pk=program_discipline_id)
                .values_list('educational_program_id', flat=True)
                .first()
            )
            if program_id:
                queryset = queryset.filter(educational_program_id=program_id)
                if linked_only:
                    linked_ids = DisciplineCompetence.objects.filter(
                        program_discipline_id=program_discipline_id
                    ).values_list('competence_id', flat=True)
                    queryset = queryset.filter(id__in=linked_ids)
            else:
                queryset = queryset.none()
        elif educational_program_id:
            queryset = queryset.filter(educational_program_id=educational_program_id)

        if discipline_id:
            discipline_links = DisciplineCompetence.objects.filter(
                program_discipline__discipline_id=discipline_id
            )
            if educational_program_id:
                discipline_links = discipline_links.filter(
                    program_discipline__educational_program_id=educational_program_id
                )
            linked_ids = discipline_links.values_list('competence_id', flat=True)
            queryset = queryset.filter(id__in=linked_ids)

        if query:
            queryset = queryset.filter(Q(code__icontains=query) | Q(name__icontains=query))

        results = [
            {'id': obj.id, 'label': f'{obj.code} — {obj.name}'}
            for obj in queryset.distinct()[:limit]
        ]
        return JsonResponse({'results': results})

    if kind == 'assessment_item_type':
        queryset = AssessmentItemType.objects.order_by('name')
        if query:
            queryset = queryset.filter(name__icontains=query)
        results = [{'id': obj.id, 'label': obj.name} for obj in queryset[:limit]]
        return JsonResponse({'results': results})

    return JsonResponse({'results': []})
