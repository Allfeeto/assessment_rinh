from django.contrib import admin

from .models import Department, EducationLevel, EducationalProgram


@admin.register(EducationLevel)
class EducationLevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_name', 'full_name')
    search_fields = ('short_name', 'full_name')


@admin.register(EducationalProgram)
class EducationalProgramAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'education_level', 'department')
    search_fields = ('code', 'name')
    list_filter = ('education_level', 'department')