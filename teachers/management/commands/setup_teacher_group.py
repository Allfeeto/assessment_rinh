from django.apps import apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS

from core.permissions import SENIOR_TEACHER_GROUP_NAME, TEACHER_GROUP_NAME


class Command(BaseCommand):
    help = 'Создает/обновляет группы преподавателей с правами для рабочих сценариев.'

    TARGET_APP_LABELS = {
        'assessment',
        'competencies',
        'core',
        'disciplines',
        'programs',
        'teachers',
    }
    TEACHER_PERMISSION_CODENAMES = {
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
        'view_assessmentitemtype',
    }
    SENIOR_EXCLUDED_CODENAMES = {
        # Админка остается только для superuser; senior работает через app UI.
        'add_logentry',
        'change_logentry',
        'delete_logentry',
        'view_logentry',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--group-name',
            default=TEACHER_GROUP_NAME,
            help='Название группы обычных преподавателей (legacy alias).',
        )
        parser.add_argument(
            '--teacher-group-name',
            default=None,
            help='Название группы обычных преподавателей.',
        )
        parser.add_argument(
            '--senior-group-name',
            default=SENIOR_TEACHER_GROUP_NAME,
            help='Название группы старших преподавателей.',
        )

    def handle(self, *args, **options):
        for app_config in apps.get_app_configs():
            if app_config.label in self.TARGET_APP_LABELS:
                create_permissions(
                    app_config,
                    verbosity=0,
                    using=DEFAULT_DB_ALIAS,
                )

        teacher_group_name = (
            options['teacher_group_name'] or options['group_name'] or TEACHER_GROUP_NAME
        ).strip() or TEACHER_GROUP_NAME
        senior_group_name = (options['senior_group_name'] or SENIOR_TEACHER_GROUP_NAME).strip()
        senior_group_name = senior_group_name or SENIOR_TEACHER_GROUP_NAME

        teacher_permissions = Permission.objects.filter(
            content_type__app_label__in=self.TARGET_APP_LABELS,
            codename__in=self.TEACHER_PERMISSION_CODENAMES,
        )
        found_codenames = set(teacher_permissions.values_list('codename', flat=True))
        missing = sorted(self.TEACHER_PERMISSION_CODENAMES - found_codenames)

        senior_permissions = Permission.objects.filter(
            content_type__app_label__in=self.TARGET_APP_LABELS,
        ).exclude(codename__in=self.SENIOR_EXCLUDED_CODENAMES)

        self._set_group_permissions(teacher_group_name, teacher_permissions)
        self.stdout.write(f'Права "{teacher_group_name}": {teacher_permissions.count()}.')
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    'Не найдены права (возможно, ещё не созданы content types/permissions): '
                    + ', '.join(missing)
                )
            )

        self._set_group_permissions(senior_group_name, senior_permissions)
        self.stdout.write(f'Права "{senior_group_name}": {senior_permissions.count()}.')

    def _set_group_permissions(self, group_name, permissions):
        group, created = Group.objects.get_or_create(name=group_name)
        group.permissions.set(permissions)

        if created:
            self.stdout.write(self.style.SUCCESS(f'Группа "{group_name}" создана.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Группа "{group_name}" обновлена.'))
