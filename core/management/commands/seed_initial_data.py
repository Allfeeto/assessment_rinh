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
        assessment_types = [
            'выбор одного ответа',
            'выбор нескольких ответов',
            'установление соответствия',
            'установление последовательности',
            'открытый ответ',
        ]
        legacy_assessment_type_map = {
            'single_choice': 'выбор одного ответа',
            'multiple_choice': 'выбор нескольких ответов',
            'matching': 'установление соответствия',
            'sequence': 'установление последовательности',
            'open_answer': 'открытый ответ',
        }
        academic_degrees = ['кандидат наук', 'доктор наук']
        academic_titles = ['доцент', 'профессор']

        with transaction.atomic():
            self._migrate_legacy_assessment_types(legacy_assessment_type_map)
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

    def _migrate_legacy_assessment_types(self, name_map):
        for legacy_name, actual_name in name_map.items():
            legacy = AssessmentItemType.objects.filter(name=legacy_name).first()
            if not legacy:
                continue
            if AssessmentItemType.objects.filter(name=actual_name).exists():
                self.stdout.write(
                    f'Тип задания: "{legacy_name}" не перенесён, т.к. "{actual_name}" уже существует.'
                )
                continue
            legacy.name = actual_name
            legacy.save(update_fields=['name'])
            self.stdout.write(f'Тип задания: "{legacy_name}" -> "{actual_name}" — обновлено.')
