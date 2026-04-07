from django.contrib import admin

from .models import EducationalProgram, ProgramProfile, TrainingDirection


@admin.register(TrainingDirection)
class TrainingDirectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'education_level')
    search_fields = ('code', 'name')
    list_filter = ('education_level',)


@admin.register(ProgramProfile)
class ProgramProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'training_direction')
    search_fields = ('code', 'name', 'training_direction__code')
    list_filter = ('training_direction',)


@admin.register(EducationalProgram)
class EducationalProgramAdmin(admin.ModelAdmin):
    list_display = ('id', 'program_profile', 'department', 'admission_year')
    search_fields = (
        'program_profile__code',
        'program_profile__name',
        'department__short_name',
        'admission_year',
    )
    list_filter = (
        'program_profile__training_direction__education_level',
        'program_profile__training_direction',
        'program_profile',
        'department',
        'admission_year',
    )