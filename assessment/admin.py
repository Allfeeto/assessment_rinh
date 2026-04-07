from django.contrib import admin

from .models import AssessmentItem, AssessmentItemRow
from .services import get_competences_for_item


class AssessmentItemRowInline(admin.TabularInline):
    model = AssessmentItemRow
    extra = 0


@admin.register(AssessmentItem)
class AssessmentItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'program_discipline', 'assessment_item_type', 'short_prompt', 'competence_codes')
    search_fields = (
        'prompt_text',
        'program_discipline__discipline__name',
        'program_discipline__educational_program__program_profile__code',
    )
    list_filter = (
        'assessment_item_type',
        'program_discipline__educational_program__program_profile__training_direction__education_level',
        'program_discipline__educational_program__program_profile__training_direction',
        'program_discipline__educational_program__program_profile',
        'program_discipline__discipline',
    )
    inlines = (AssessmentItemRowInline,)

    @staticmethod
    def short_prompt(obj):
        return obj.prompt_text[:120]

    @staticmethod
    def competence_codes(obj):
        competences = get_competences_for_item(obj.id)
        return ', '.join(comp.code for comp in competences)


@admin.register(AssessmentItemRow)
class AssessmentItemRowAdmin(admin.ModelAdmin):
    list_display = ('id', 'assessment_item', 'row_kind', 'left_text', 'right_text', 'is_correct', 'sort_order', 'correct_order')
    search_fields = ('left_text', 'right_text', 'open_answer_text', 'assessment_item__prompt_text')
    list_filter = ('row_kind',)