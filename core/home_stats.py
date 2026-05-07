from __future__ import annotations

from django.conf import settings
from django.core.cache import cache

from assessment.access import program_discipline_queryset_for_user
from assessment.models import AssessmentItem
from competencies.models import Competence
from disciplines.models import Discipline
from programs.models import EducationalProgram, ProgramProfile, TrainingDirection
from teachers.models import Department, Teacher

from .models import EducationLevel
from .permissions import is_staff_or_superuser


HOME_STATS_CACHE_KEY = 'core:home_stats'


def build_home_stats():
    return {
        'education_levels': EducationLevel.objects.count(),
        'departments': Department.objects.count(),
        'teachers': Teacher.objects.count(),
        'training_directions': TrainingDirection.objects.count(),
        'program_profiles': ProgramProfile.objects.count(),
        'educational_programs': EducationalProgram.objects.active().count(),
        'disciplines': Discipline.objects.count(),
        'competences': Competence.objects.filter(educational_program__is_deleted=False).count(),
        'assessment_items': AssessmentItem.objects.filter(
            program_discipline__educational_program__is_deleted=False
        ).count(),
    }


def build_scoped_home_stats(user):
    program_discipline_scope = program_discipline_queryset_for_user(user)
    program_ids = program_discipline_scope.values_list('educational_program_id', flat=True)
    discipline_ids = program_discipline_scope.values_list('discipline_id', flat=True)
    program_discipline_ids = program_discipline_scope.values_list('id', flat=True)

    return {
        'educational_programs': EducationalProgram.objects.active()
        .filter(id__in=program_ids)
        .distinct()
        .count(),
        'disciplines': Discipline.objects.filter(id__in=discipline_ids).distinct().count(),
        'competences': Competence.objects.filter(
            educational_program__is_deleted=False,
            educational_program_id__in=program_ids,
        ).distinct().count(),
        'assessment_items': AssessmentItem.objects.filter(
            program_discipline__educational_program__is_deleted=False,
            program_discipline_id__in=program_discipline_ids,
        ).count(),
    }


def get_home_stats_for_user(user):
    if not is_staff_or_superuser(user):
        return build_scoped_home_stats(user)

    ttl = getattr(settings, 'HOME_STATS_CACHE_TTL', 60)
    stats = cache.get(HOME_STATS_CACHE_KEY)
    if stats is None:
        stats = build_home_stats()
        cache.set(HOME_STATS_CACHE_KEY, stats, ttl)
    return stats
