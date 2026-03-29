from django.core.management.base import BaseCommand
from django.db import transaction

from assessment.models import AssessmentItemType
from competencies.models import CompetenceType


class Command(BaseCommand):
    help = 'Заполнение типов компетенций и типов заданий начальными данными.'

    def handle(self, *args, **options):
        competence_types = ['УК', 'ОПК', 'ПК']
        assessment_item_types = [
            'соответствие',
            'последовательность',
            'несколько',
            'один',
            'открытый',
        ]

        with transaction.atomic():
            for name in competence_types:
                _, created = CompetenceType.objects.get_or_create(name=name)
                action = 'создан' if created else 'уже существует'
                self.stdout.write(f'Тип компетенции "{name}" {action}.')

            for name in assessment_item_types:
                _, created = AssessmentItemType.objects.get_or_create(name=name)
                action = 'создан' if created else 'уже существует'
                self.stdout.write(f'Тип задания "{name}" {action}.')

        self.stdout.write(self.style.SUCCESS('Начальные данные успешно загружены.'))