from django.contrib import admin

from .models import (
    AcademicDegree,
    AcademicTitle,
    AssessmentItemType,
    CompetenceType,
    EducationLevel,
)


@admin.register(EducationLevel)
class EducationLevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(CompetenceType)
class CompetenceTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(AssessmentItemType)
class AssessmentItemTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(AcademicDegree)
class AcademicDegreeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(AcademicTitle)
class AcademicTitleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)