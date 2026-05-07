from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.schema_contract import (
    check_live_database_contract,
    check_sql_schema_contract,
    configured_schema_sql_path,
)


class Command(BaseCommand):
    help = 'Проверяет совместимость unmanaged Django-моделей с SQL-схемой проекта.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sql',
            default=None,
            help='Путь к SQL-файлу схемы. По умолчанию используется DB_SCHEMA_SQL_PATH.',
        )
        parser.add_argument(
            '--live',
            action='store_true',
            help='Дополнительно проверить фактическую подключенную базу данных.',
        )
        parser.add_argument(
            '--database',
            default='default',
            help='Алиас Django database для --live проверки.',
        )

    def handle(self, *args, **options):
        sql_path = Path(options['sql']) if options['sql'] else configured_schema_sql_path()
        if sql_path is None and not options['live']:
            raise CommandError(
                'Укажите --live для проверки подключенной БД или --sql/DB_SCHEMA_SQL_PATH '
                'для проверки приватного SQL-файла.'
            )

        issues = []
        if sql_path is not None:
            issues.extend(check_sql_schema_contract(sql_path))
        if options['live']:
            issues.extend(check_live_database_contract(options['database']))

        if issues:
            for issue in issues:
                self.stderr.write(self.style.ERROR(issue.message))
            raise CommandError(f'Проверка схемы не пройдена: {len(issues)} проблем.')

        targets = []
        if sql_path is not None:
            targets.append(str(sql_path))
        if options['live']:
            targets.append(f'БД {options["database"]}')
        self.stdout.write(self.style.SUCCESS(
            f'Схема {", ".join(targets)} совместима с Django-моделями.'
        ))
