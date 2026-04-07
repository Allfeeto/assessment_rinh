from django.contrib import admin

from .models import Competence, DisciplineCompetence


@admin.register(Competence)
class CompetenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'competence_type', 'educational_program')
    search_fields = ('code', 'name', 'educational_program__program_profile__code')
    list_filter = (
        'competence_type',
        'educational_program__program_profile__training_direction__education_level',
        'educational_program__program_profile__training_direction',
        'educational_program__program_profile',
        'educational_program__admission_year',
    )


@admin.register(DisciplineCompetence)
class DisciplineCompetenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'program_discipline', 'competence')
    search_fields = (
        'program_discipline__discipline__name',
        'competence__code',
        'competence__name',
    )
    list_filter = (
        'program_discipline__educational_program__program_profile__training_direction__education_level',
        'program_discipline__educational_program__program_profile__training_direction',
        'program_discipline__educational_program__program_profile',
    )