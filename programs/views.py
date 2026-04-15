from django.http import JsonResponse
from django.views.generic import TemplateView

from core.view_helpers import (
    NamedCreateView,
    NamedDeleteView,
    NamedDetailView,
    NamedListView,
    NamedUpdateView,
)

from .forms import EducationalProgramForm, ProgramProfileForm, TrainingDirectionForm
from .models import EducationalProgram, ProgramProfile, TrainingDirection


class ProgramsDashboardView(TemplateView):
    template_name = 'programs/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['directions'] = TrainingDirection.objects.select_related('education_level').order_by('code')
        context['profiles'] = ProgramProfile.objects.select_related('training_direction').order_by('code')
        context['programs'] = EducationalProgram.objects.select_related(
            'program_profile__training_direction',
            'department',
        ).order_by('program_profile__code', 'admission_year')
        return context


class TrainingDirectionListView(NamedListView):
    model = TrainingDirection
    title = 'Направления подготовки'
    search_fields = ('code', 'name')
    list_columns = (
        ('ID', 'id'),
        ('Код', 'code'),
        ('Наименование', 'name'),
        ('Уровень', 'education_level.name'),
    )
    create_url_name = 'programs_direction_create'
    detail_url_name = 'programs_direction_detail'
    update_url_name = 'programs_direction_update'
    delete_url_name = 'programs_direction_delete'


class TrainingDirectionDetailView(NamedDetailView):
    model = TrainingDirection
    title = 'Карточка направления'
    list_url_name = 'programs_direction_list'
    update_url_name = 'programs_direction_update'
    delete_url_name = 'programs_direction_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Код', 'code'),
        ('Наименование', 'name'),
        ('Уровень', 'education_level.name'),
    )


class TrainingDirectionCreateView(NamedCreateView):
    model = TrainingDirection
    form_class = TrainingDirectionForm
    title = 'Создать направление'
    list_url_name = 'programs_direction_list'


class TrainingDirectionUpdateView(NamedUpdateView):
    model = TrainingDirection
    form_class = TrainingDirectionForm
    title = 'Редактировать направление'
    list_url_name = 'programs_direction_list'


class TrainingDirectionDeleteView(NamedDeleteView):
    model = TrainingDirection
    title = 'Удалить направление'
    list_url_name = 'programs_direction_list'


class ProgramProfileListView(NamedListView):
    model = ProgramProfile
    title = 'Профили программ'
    search_fields = ('code', 'name', 'training_direction__code')
    list_columns = (
        ('ID', 'id'),
        ('Код профиля', 'code'),
        ('Наименование', 'name'),
        ('Направление', 'training_direction.code'),
    )
    create_url_name = 'programs_profile_create'
    detail_url_name = 'programs_profile_detail'
    update_url_name = 'programs_profile_update'
    delete_url_name = 'programs_profile_delete'


class ProgramProfileDetailView(NamedDetailView):
    model = ProgramProfile
    title = 'Карточка профиля'
    list_url_name = 'programs_profile_list'
    update_url_name = 'programs_profile_update'
    delete_url_name = 'programs_profile_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Код профиля', 'code'),
        ('Наименование', 'name'),
        ('Направление', 'training_direction.code'),
    )


class ProgramProfileCreateView(NamedCreateView):
    model = ProgramProfile
    form_class = ProgramProfileForm
    title = 'Создать профиль'
    list_url_name = 'programs_profile_list'


class ProgramProfileUpdateView(NamedUpdateView):
    model = ProgramProfile
    form_class = ProgramProfileForm
    title = 'Редактировать профиль'
    list_url_name = 'programs_profile_list'


class ProgramProfileDeleteView(NamedDeleteView):
    model = ProgramProfile
    title = 'Удалить профиль'
    list_url_name = 'programs_profile_list'


class EducationalProgramListView(NamedListView):
    model = EducationalProgram
    title = 'Образовательные программы'
    search_fields = (
        'program_profile__code',
        'program_profile__name',
        'department__short_name',
    )
    list_columns = (
        ('ID', 'id'),
        ('Профиль', 'program_profile.code'),
        ('Кафедра', 'department.short_name'),
        ('Год набора', 'admission_year'),
    )
    create_url_name = 'programs_educational_program_create'
    detail_url_name = 'programs_educational_program_detail'
    update_url_name = 'programs_educational_program_update'
    delete_url_name = 'programs_educational_program_delete'


class EducationalProgramDetailView(NamedDetailView):
    model = EducationalProgram
    title = 'Карточка образовательной программы'
    list_url_name = 'programs_educational_program_list'
    update_url_name = 'programs_educational_program_update'
    delete_url_name = 'programs_educational_program_delete'
    detail_fields = (
        ('ID', 'id'),
        ('Профиль', 'program_profile.code'),
        ('Наименование профиля', 'program_profile.name'),
        ('Направление', 'program_profile.training_direction.code'),
        ('Кафедра', 'department.short_name'),
        ('Год набора', 'admission_year'),
    )


class EducationalProgramCreateView(NamedCreateView):
    model = EducationalProgram
    form_class = EducationalProgramForm
    title = 'Создать образовательную программу'
    list_url_name = 'programs_educational_program_list'


class EducationalProgramUpdateView(NamedUpdateView):
    model = EducationalProgram
    form_class = EducationalProgramForm
    title = 'Редактировать образовательную программу'
    list_url_name = 'programs_educational_program_list'


class EducationalProgramDeleteView(NamedDeleteView):
    model = EducationalProgram
    title = 'Удалить образовательную программу'
    list_url_name = 'programs_educational_program_list'


def profiles_by_direction(request):
    direction_id = request.GET.get('direction_id')
    queryset = ProgramProfile.objects.order_by('code')
    if direction_id:
        queryset = queryset.filter(training_direction_id=direction_id)

    data = [{'id': profile.id, 'label': str(profile)} for profile in queryset]
    return JsonResponse({'results': data})
