from django.views.generic import TemplateView

from assessment.models import AssessmentItem
from competencies.models import Competence
from disciplines.models import Discipline
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


class HomeView(TemplateView):
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
