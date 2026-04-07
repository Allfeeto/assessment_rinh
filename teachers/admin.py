from django.contrib import admin

from .models import Department, Teacher


class TeacherInline(admin.TabularInline):
    model = Teacher
    extra = 0
    fk_name = 'department'


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'number', 'short_name', 'head_teacher')
    search_fields = ('number', 'short_name', 'full_name')
    inlines = (TeacherInline,)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'department', 'academic_degree', 'academic_title')
    search_fields = ('full_name', 'department__short_name', 'department__number')
    list_filter = ('department', 'academic_degree', 'academic_title')