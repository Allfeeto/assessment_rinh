from django.contrib import admin

from .models import Department, Teacher, TeacherProgramDiscipline


class TeacherInline(admin.TabularInline):
    model = Teacher
    extra = 0
    fk_name = 'department'


class TeacherProgramDisciplineInline(admin.TabularInline):
    model = TeacherProgramDiscipline
    extra = 0


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'number', 'short_name', 'head_teacher')
    search_fields = ('number', 'short_name', 'full_name')
    inlines = (TeacherInline,)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'user', 'department', 'academic_degree', 'academic_title')
    search_fields = (
        'full_name',
        'user__username',
        'user__first_name',
        'user__last_name',
        'department__short_name',
        'department__number',
    )
    list_filter = ('department', 'academic_degree', 'academic_title')
    inlines = (TeacherProgramDisciplineInline,)


@admin.register(TeacherProgramDiscipline)
class TeacherProgramDisciplineAdmin(admin.ModelAdmin):
    list_display = ('id', 'teacher', 'program_discipline')
    search_fields = (
        'teacher__full_name',
        'program_discipline__discipline__name',
        'program_discipline__educational_program__program_profile__code',
    )
    list_filter = (
        'program_discipline__educational_program__program_profile__training_direction__education_level',
        'program_discipline__educational_program__program_profile__training_direction',
        'program_discipline__educational_program__program_profile',
    )
