from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    AcademicDegree,
    AcademicTitle,
    AssessmentItemType,
    CompetenceType,
    EducationLevel,
)


class Command(BaseCommand):
    help = 'Заполнение базовых справочников новой схемы БД.'

    def handle(self, *args, **options):
        education_levels = ['бакалавриат', 'магистратура', 'специалитет']
        competence_types = ['УК', 'ОПК', 'ПК']
        assessment_types = ['single_choice', 'multiple_choice', 'matching', 'sequence', 'open_answer']
        academic_degrees = ['кандидат наук', 'доктор наук']
        academic_titles = ['доцент', 'профессор']

        with transaction.atomic():
            self._seed(EducationLevel, education_levels)
            self._seed(CompetenceType, competence_types)
            self._seed(AssessmentItemType, assessment_types)
            self._seed(AcademicDegree, academic_degrees)
            self._seed(AcademicTitle, academic_titles)

        self.stdout.write(self.style.SUCCESS('Справочники заполнены.'))

    def _seed(self, model, values):
        for value in values:
            _, created = model.objects.get_or_create(name=value)
            msg = 'создано' if created else 'уже было'
            self.stdout.write(f'{model._meta.verbose_name}: "{value}" — {msg}.')