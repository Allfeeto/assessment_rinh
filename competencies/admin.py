from django.contrib import admin

from .models import Competence, CompetenceType, DisciplineCompetence


@admin.register(CompetenceType)
class CompetenceTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Competence)
class CompetenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'competence_type', 'educational_program')
    search_fields = ('code', 'name', 'educational_program__code', 'educational_program__name')
    list_filter = ('competence_type', 'educational_program')


@admin.register(DisciplineCompetence)
class DisciplineCompetenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'program_discipline', 'competence')
    search_fields = (
        'program_discipline__discipline__name',
        'program_discipline__educational_program__code',
        'competence__code',
        'competence__name',
    )
    list_filter = (
        'program_discipline__educational_program',
        'program_discipline__discipline',
        'competence__competence_type',
    )