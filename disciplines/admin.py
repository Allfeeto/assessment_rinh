from django.contrib import admin

from .models import Discipline, ProgramDiscipline


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(ProgramDiscipline)
class ProgramDisciplineAdmin(admin.ModelAdmin):
    list_display = ('id', 'educational_program', 'discipline_code', 'discipline', 'department')
    search_fields = (
        'educational_program__program_profile__code',
        'educational_program__program_profile__name',
        'discipline_code',
        'discipline__name',
        'department__number',
        'department__short_name',
    )
    list_filter = (
        'educational_program__program_profile__training_direction__education_level',
        'educational_program__program_profile__training_direction',
        'educational_program__program_profile',
        'educational_program__admission_year',
        'department',
    )
