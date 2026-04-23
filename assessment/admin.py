from django.contrib import admin

from .models import AssessmentItem, AssessmentItemCompetence, AssessmentItemRow
from .services import get_item_type_ui_name


class AssessmentItemRowInline(admin.TabularInline):
    model = AssessmentItemRow
    extra = 0
    fields = ('left_text', 'right_text', 'correct_order', 'is_correct', 'open_answer_text', 'sort_order')


class AssessmentItemCompetenceInline(admin.TabularInline):
    model = AssessmentItemCompetence
    extra = 0


@admin.register(AssessmentItem)
class AssessmentItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'program_discipline',
        'competence',
        'item_type_name',
        'short_prompt',
    )
    search_fields = (
        'prompt_text',
        'program_discipline__discipline__name',
        'program_discipline__educational_program__program_profile__code',
        'competence__code',
        'competence__name',
    )
    list_filter = (
        'assessment_item_type',
        'program_discipline__educational_program__program_profile__training_direction__education_level',
        'program_discipline__educational_program__program_profile__training_direction',
        'program_discipline__educational_program__program_profile',
        'program_discipline__discipline',
        'competence__competence_type',
    )
    inlines = (AssessmentItemCompetenceInline, AssessmentItemRowInline)

    @staticmethod
    def short_prompt(obj):
        return obj.prompt_text[:120]

    @staticmethod
    def item_type_name(obj):
        return get_item_type_ui_name(obj.assessment_item_type.name)

    item_type_name.short_description = 'Тип задания'


@admin.register(AssessmentItemRow)
class AssessmentItemRowAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'assessment_item',
        'left_text',
        'right_text',
        'correct_order',
        'is_correct',
        'open_answer_text',
        'sort_order',
    )
    search_fields = ('left_text', 'right_text', 'open_answer_text', 'assessment_item__prompt_text')


@admin.register(AssessmentItemCompetence)
class AssessmentItemCompetenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'assessment_item', 'competence')
    search_fields = (
        'assessment_item__prompt_text',
        'competence__code',
        'competence__name',
    )
