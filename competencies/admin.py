from django.contrib import admin

from .models import (
    Competence,
    CompetenceIndicator,
    CompetenceIndicatorImport,
    DisciplineCompetence,
)


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


@admin.register(CompetenceIndicator)
class CompetenceIndicatorAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'competence', 'source_file', 'updated_at')
    search_fields = ('code', 'text', 'competence__code', 'competence__name')
    list_filter = (
        'competence__educational_program__program_profile',
        'competence__competence_type',
    )


@admin.register(CompetenceIndicatorImport)
class CompetenceIndicatorImportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'source_filename',
        'educational_program',
        'status',
        'created_count',
        'updated_count',
        'skipped_count',
        'error_count',
        'created_at',
    )
    search_fields = ('source_filename', 'source_sha256', 'educational_program__program_profile__code')
    list_filter = ('status', 'educational_program__program_profile', 'created_at')
    readonly_fields = (
        'source_sha256',
        'status',
        'total_rows',
        'created_count',
        'updated_count',
        'skipped_count',
        'error_count',
        'warning_count',
        'error_summary',
        'created_at',
        'completed_at',
    )
