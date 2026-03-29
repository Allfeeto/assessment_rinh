from django.contrib import admin

from .models import Discipline, ProgramDiscipline


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(ProgramDiscipline)
class ProgramDisciplineAdmin(admin.ModelAdmin):
    list_display = ('id', 'educational_program', 'discipline')
    search_fields = (
        'educational_program__code',
        'educational_program__name',
        'discipline__name',
    )
    list_filter = ('educational_program', 'discipline')