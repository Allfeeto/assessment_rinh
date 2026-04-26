from django.core.management.base import BaseCommand
from django.db import transaction

from assessment.services import TYPE_MATCHING, TYPE_MULTIPLE, TYPE_OPEN, TYPE_SEQUENCE, TYPE_SINGLE
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
            (TYPE_SINGLE, 'выбор одного ответа'),
            (TYPE_MULTIPLE, 'выбор нескольких ответов'),
            (TYPE_MATCHING, 'установление соответствия'),
            (TYPE_SEQUENCE, 'установление последовательности'),
            (TYPE_OPEN, 'открытый ответ'),
        ]
        legacy_assessment_type_map = {
            'single_choice': (TYPE_SINGLE, 'выбор одного ответа'),
            'multiple_choice': (TYPE_MULTIPLE, 'выбор нескольких ответов'),
            'matching': (TYPE_MATCHING, 'установление соответствия'),
            'sequence': (TYPE_SEQUENCE, 'установление последовательности'),
            'open_answer': (TYPE_OPEN, 'открытый ответ'),
        }
        academic_degrees = ['к.н.', 'д.э.н.']
        academic_titles = ['доцент', 'профессор']

        with transaction.atomic():
            self._migrate_legacy_assessment_types(legacy_assessment_type_map)
            self._seed(EducationLevel, education_levels)
            self._seed(CompetenceType, competence_types)
            self._seed_assessment_item_types(assessment_types)
            self._seed(AcademicDegree, academic_degrees)
            self._seed(AcademicTitle, academic_titles)

        self.stdout.write(self.style.SUCCESS('Справочники заполнены.'))

    def _seed(self, model, values):
        for value in values:
            _, created = model.objects.get_or_create(name=value)
            msg = 'создано' if created else 'уже было'
            self.stdout.write(f'{model._meta.verbose_name}: "{value}" — {msg}.')

    def _seed_assessment_item_types(self, values):
        for code, name in values:
            item_type = AssessmentItemType.objects.filter(code=code).first()
            created = False
            if item_type is None:
                item_type = AssessmentItemType.objects.filter(name=name).first()
            if item_type is None:
                item_type = AssessmentItemType.objects.create(code=code, name=name)
                created = True
            elif item_type.code != code or item_type.name != name:
                existing_name = AssessmentItemType.objects.filter(name=name).exclude(pk=item_type.pk).first()
                if existing_name:
                    self.stdout.write(
                        f'{AssessmentItemType._meta.verbose_name}: "{code}" не переименован, '
                        f'т.к. "{name}" уже существует.'
                    )
                else:
                    item_type.code = code
                    item_type.name = name
                    item_type.save(update_fields=['code', 'name'])
            msg = 'создано' if created else 'уже было'
            self.stdout.write(f'{AssessmentItemType._meta.verbose_name}: "{code}" — {name} — {msg}.')

    def _migrate_legacy_assessment_types(self, name_map):
        for legacy_name, (actual_code, actual_name) in name_map.items():
            legacy = AssessmentItemType.objects.filter(name=legacy_name).first()
            if not legacy:
                continue
            existing = AssessmentItemType.objects.filter(code=actual_code).exclude(pk=legacy.pk).first()
            if existing:
                self.stdout.write(
                    f'Тип задания: "{legacy_name}" не перенесён, т.к. код "{actual_code}" уже существует.'
                )
                continue
            existing_name = AssessmentItemType.objects.filter(name=actual_name).exclude(pk=legacy.pk).first()
            if existing_name:
                self.stdout.write(
                    f'Тип задания: "{legacy_name}" не перенесён, т.к. "{actual_name}" уже существует.'
                )
                continue
            legacy.code = actual_code
            legacy.name = actual_name
            legacy.save(update_fields=['code', 'name'])
            self.stdout.write(f'Тип задания: "{legacy_name}" -> "{actual_code}" — "{actual_name}" — обновлено.')
