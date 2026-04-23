from django.apps import apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS


class Command(BaseCommand):
    help = 'Создает/обновляет группу "Преподаватель" с базовыми правами для рабочего сценария.'

    DEFAULT_GROUP_NAME = 'Преподаватель'

    PERMISSION_CODENAMES = {
        # Работа преподавателя с заданиями.
        'view_assessmentitem',
        'add_assessmentitem',
        'change_assessmentitem',
        'delete_assessmentitem',
        'view_assessmentitemrow',
        'add_assessmentitemrow',
        'change_assessmentitemrow',
        'delete_assessmentitemrow',
        'view_assessmentitemcompetence',
        'add_assessmentitemcompetence',
        'change_assessmentitemcompetence',
        'delete_assessmentitemcompetence',
        # Контекст учебного плана и компетенций.
        'view_educationalprogram',
        'view_programprofile',
        'view_trainingdirection',
        'view_programdiscipline',
        'view_discipline',
        'view_competence',
        'view_disciplinecompetence',
        'view_assessmentitemtype',
        # Просмотр данных преподавателей и назначений.
        'view_teacher',
        'view_department',
        'view_teacherprogramdiscipline',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--group-name',
            default=self.DEFAULT_GROUP_NAME,
            help='Название группы (по умолчанию: "Преподаватель").',
        )

    def handle(self, *args, **options):
        target_app_labels = {
            'assessment',
            'competencies',
            'core',
            'disciplines',
            'programs',
            'teachers',
        }
        for app_config in apps.get_app_configs():
            if app_config.label in target_app_labels:
                create_permissions(
                    app_config,
                    verbosity=0,
                    using=DEFAULT_DB_ALIAS,
                )

        group_name = options['group_name'].strip() or self.DEFAULT_GROUP_NAME
        group, created = Group.objects.get_or_create(name=group_name)

        permissions = Permission.objects.filter(codename__in=self.PERMISSION_CODENAMES)
        found_codenames = set(permissions.values_list('codename', flat=True))
        missing = sorted(self.PERMISSION_CODENAMES - found_codenames)

        group.permissions.set(permissions)

        if created:
            self.stdout.write(self.style.SUCCESS(f'Группа "{group_name}" создана.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Группа "{group_name}" обновлена.'))

        self.stdout.write(f'Назначено прав: {permissions.count()}.')
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    'Не найдены права (возможно, ещё не созданы content types/permissions): '
                    + ', '.join(missing)
                )
            )
