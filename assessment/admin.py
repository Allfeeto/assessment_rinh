from django.contrib import admin

from .models import (
    AssessmentItem,
    AssessmentItemCompetence,
    AssessmentItemType,
    AssessmentMatchLeftItem,
    AssessmentMatchRightItem,
    AssessmentOpenAnswer,
    AssessmentOption,
    AssessmentSequenceItem,
)


class AssessmentOptionInline(admin.TabularInline):
    model = AssessmentOption
    extra = 1


class AssessmentMatchingLeftInline(admin.TabularInline):
    model = AssessmentMatchLeftItem
    extra = 1


class AssessmentMatchingRightInline(admin.TabularInline):
    model = AssessmentMatchRightItem
    extra = 1


class AssessmentSequenceInline(admin.TabularInline):
    model = AssessmentSequenceItem
    extra = 1


class AssessmentOpenAnswerInline(admin.TabularInline):
    model = AssessmentOpenAnswer
    extra = 1


@admin.register(AssessmentItemType)
class AssessmentItemTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(AssessmentItem)
class AssessmentItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'program_discipline', 'assessment_item_type', 'short_text')
    search_fields = (
        'text',
        'program_discipline__educational_program__code',
        'program_discipline__educational_program__name',
        'program_discipline__discipline__name',
    )
    list_filter = (
        'assessment_item_type',
        'program_discipline__educational_program',
        'program_discipline__discipline',
    )
    inlines = (
        AssessmentOptionInline,
        AssessmentMatchingLeftInline,
        AssessmentMatchingRightInline,
        AssessmentSequenceInline,
        AssessmentOpenAnswerInline,
    )

    @staticmethod
    def short_text(obj):
        return obj.text[:120]


@admin.register(AssessmentItemCompetence)
class AssessmentItemCompetenceAdmin(admin.ModelAdmin):
    list_display = ('assessment_item', 'competence')
    search_fields = ('assessment_item__text', 'competence__code', 'competence__name')
    list_filter = ('competence__competence_type',)
