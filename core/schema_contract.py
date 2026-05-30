from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections, models


REQUIRED_CONSTRAINTS = {
    'assessment_item_row_check',
    'assessment_item_row_correct_order_check',
    'assessment_item_row_sort_order_check',
    'educational_program_admission_year_check',
}
REQUIRED_INDEXES = {
    'educational_program_active_unique_idx',
    'program_disc_code_idx',
    'program_disc_dept_idx',
    'program_disc_prog_code_idx',
    'teacher_departments_department_idx',
    'teacher_departments_teacher_department_uidx',
    'teacher_departments_teacher_idx',
    'uq_assessment_item_row_correct_order',
    'uq_assessment_item_row_sort',
}
REQUIRED_TABLES = {
    'teacher_departments',
}
REQUIRED_FUNCTIONS = {
    'check_assessment_item_relation_integrity',
    'check_assessment_item_competence_relation_integrity',
    'check_assessment_item_row_by_type',
    'check_discipline_competence_same_program',
    'check_program_profile_code_prefix',
}
REQUIRED_TRIGGERS = {
    'trg_check_assessment_item_relation_integrity',
    'trg_check_assessment_item_competence_relation_integrity',
    'trg_check_assessment_item_row_by_type',
    'trg_check_discipline_competence_same_program',
    'trg_check_program_profile_code_prefix',
}

TABLE_RE = re.compile(
    r'CREATE TABLE public\.([a-zA-Z_][\w]*) \(\s*\n(?P<body>.*?)\n\);',
    re.DOTALL,
)
COLUMN_RE = re.compile(r'^\s+([a-zA-Z_][\w]*)\s+(.+?)(?:,)?$')


@dataclass(frozen=True)
class SQLColumn:
    name: str
    definition: str
    sql_type: str
    not_null: bool


@dataclass(frozen=True)
class SQLTable:
    name: str
    columns: dict[str, SQLColumn]


@dataclass(frozen=True)
class ParsedSQLSchema:
    tables: dict[str, SQLTable]
    constraints: set[str]
    indexes: set[str]
    functions: set[str]
    triggers: set[str]


@dataclass(frozen=True)
class SchemaContractIssue:
    message: str


def configured_schema_sql_path() -> Path | None:
    raw_path = getattr(settings, 'DB_SCHEMA_SQL_PATH', None)
    return Path(raw_path) if raw_path else None


def _normalize_sql_type(definition: str) -> str:
    value = definition.strip().rstrip(',')
    lower = value.lower()
    stop_indexes = [
        lower.find(token)
        for token in (' default ', ' not null', ' null', ' constraint ', ' check ', ' collate ')
        if lower.find(token) != -1
    ]
    if stop_indexes:
        value = value[:min(stop_indexes)]
    return ' '.join(value.lower().split())


def _parse_columns(body: str) -> dict[str, SQLColumn]:
    columns = {}
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('CONSTRAINT '):
            continue
        match = COLUMN_RE.match(raw_line)
        if not match:
            continue
        name, definition = match.groups()
        columns[name] = SQLColumn(
            name=name,
            definition=definition.strip().rstrip(','),
            sql_type=_normalize_sql_type(definition),
            not_null=' NOT NULL' in f' {definition.upper()}',
        )
    return columns


def parse_sql_schema(sql_text: str) -> ParsedSQLSchema:
    sql_text = textwrap.dedent(sql_text)
    tables = {
        match.group(1): SQLTable(
            name=match.group(1),
            columns=_parse_columns(match.group('body')),
        )
        for match in TABLE_RE.finditer(sql_text)
    }
    constraints = set(re.findall(r'\bCONSTRAINT\s+([a-zA-Z_][\w]*)\b', sql_text))
    indexes = set(re.findall(r'\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+([a-zA-Z_][\w]*)\b', sql_text))
    functions = set(re.findall(r'\bCREATE\s+FUNCTION\s+public\.([a-zA-Z_][\w]*)\s*\(', sql_text))
    triggers = set(re.findall(r'\bCREATE\s+TRIGGER\s+([a-zA-Z_][\w]*)\b', sql_text))
    return ParsedSQLSchema(
        tables=tables,
        constraints=constraints,
        indexes=indexes,
        functions=functions,
        triggers=triggers,
    )


def load_sql_schema(path: Path) -> ParsedSQLSchema:
    sql_path = Path(path)
    return parse_sql_schema(sql_path.read_text(encoding='utf-8'))


def external_schema_models():
    app_labels = set(settings.LOCAL_APPS_WITH_EXTERNAL_SCHEMA)
    return [
        model
        for model in apps.get_models(include_auto_created=False)
        if model._meta.app_label in app_labels and not model._meta.managed
    ]


def _field_expected_type_prefixes(field: models.Field) -> tuple[str, ...]:
    internal_type = field.get_internal_type()
    if isinstance(field, models.ForeignKey):
        internal_type = field.target_field.get_internal_type()

    mapping = {
        'AutoField': ('integer',),
        'BigAutoField': ('bigint',),
        'SmallAutoField': ('smallint',),
        'IntegerField': ('integer',),
        'SmallIntegerField': ('smallint',),
        'BigIntegerField': ('bigint',),
        'BooleanField': ('boolean',),
        'CharField': ('character varying', 'varchar'),
        'TextField': ('text',),
        'DateTimeField': ('timestamp with time zone', 'timestamp'),
    }
    return mapping.get(internal_type, ())


def _field_type_matches(field: models.Field, sql_type: str) -> bool:
    expected = _field_expected_type_prefixes(field)
    if not expected:
        return True
    return any(sql_type.startswith(prefix) for prefix in expected)


def _check_required_objects(schema: ParsedSQLSchema) -> list[SchemaContractIssue]:
    issues = []
    for name in sorted(REQUIRED_TABLES - set(schema.tables)):
        issues.append(SchemaContractIssue(f'В SQL-схеме отсутствует table {name}.'))
    for name in sorted(REQUIRED_CONSTRAINTS - schema.constraints):
        issues.append(SchemaContractIssue(f'В SQL-схеме отсутствует constraint {name}.'))
    for name in sorted(REQUIRED_INDEXES - schema.indexes):
        issues.append(SchemaContractIssue(f'В SQL-схеме отсутствует index {name}.'))
    for name in sorted(REQUIRED_FUNCTIONS - schema.functions):
        issues.append(SchemaContractIssue(f'В SQL-схеме отсутствует function {name}.'))
    for name in sorted(REQUIRED_TRIGGERS - schema.triggers):
        issues.append(SchemaContractIssue(f'В SQL-схеме отсутствует trigger {name}.'))
    return issues


def check_parsed_sql_schema_contract(schema: ParsedSQLSchema) -> list[SchemaContractIssue]:
    issues = _check_required_objects(schema)

    for model in external_schema_models():
        table = schema.tables.get(model._meta.db_table)
        if table is None:
            issues.append(SchemaContractIssue(
                f'Для модели {model._meta.label} в SQL-схеме отсутствует таблица {model._meta.db_table}.'
            ))
            continue

        for field in model._meta.local_fields:
            column = table.columns.get(field.column)
            if column is None:
                issues.append(SchemaContractIssue(
                    f'Для поля {model._meta.label}.{field.name} отсутствует колонка '
                    f'{model._meta.db_table}.{field.column}.'
                ))
                continue
            if not _field_type_matches(field, column.sql_type):
                issues.append(SchemaContractIssue(
                    f'Тип поля {model._meta.label}.{field.name} не совпадает с SQL: '
                    f'ожидался {field.get_internal_type()}, в SQL {column.sql_type}.'
                ))
            if not field.null and not column.not_null:
                issues.append(SchemaContractIssue(
                    f'Колонка {model._meta.db_table}.{field.column} должна быть NOT NULL по Django-модели.'
                ))

    return issues


def check_sql_schema_contract(path: Path | None = None) -> list[SchemaContractIssue]:
    sql_path = path or configured_schema_sql_path()
    if sql_path is None:
        raise ValueError('SQL-схема не задана. Передайте --sql или DB_SCHEMA_SQL_PATH.')

    return check_parsed_sql_schema_contract(load_sql_schema(sql_path))


def check_live_database_contract(using: str = DEFAULT_DB_ALIAS) -> list[SchemaContractIssue]:
    connection = connections[using]
    issues = []
    with connection.cursor() as cursor:
        table_names = set(connection.introspection.table_names(cursor))
        db_objects = set()

        for table_name in sorted(REQUIRED_TABLES - table_names):
            issues.append(SchemaContractIssue(f'В базе отсутствует таблица {table_name}.'))

        for table_name in sorted(REQUIRED_TABLES & table_names):
            db_objects.update(connection.introspection.get_constraints(cursor, table_name).keys())

        for model in external_schema_models():
            table_name = model._meta.db_table
            if table_name not in table_names:
                issues.append(SchemaContractIssue(
                    f'В базе отсутствует таблица {table_name} для модели {model._meta.label}.'
                ))
                continue

            description = connection.introspection.get_table_description(cursor, table_name)
            columns = {column.name for column in description}
            missing_columns = {
                field.column
                for field in model._meta.local_fields
                if field.column not in columns
            }
            for column in sorted(missing_columns):
                issues.append(SchemaContractIssue(f'В базе отсутствует колонка {table_name}.{column}.'))

            db_objects.update(connection.introspection.get_constraints(cursor, table_name).keys())

        for name in sorted((REQUIRED_CONSTRAINTS | REQUIRED_INDEXES) - db_objects):
            issues.append(SchemaContractIssue(f'В базе отсутствует constraint/index {name}.'))

        if connection.vendor == 'postgresql':
            cursor.execute(
                """
                SELECT tgname
                FROM pg_trigger
                WHERE NOT tgisinternal
                """
            )
            triggers = {row[0] for row in cursor.fetchall()}
            cursor.execute(
                """
                SELECT proname
                FROM pg_proc
                WHERE pronamespace = 'public'::regnamespace
                """
            )
            functions = {row[0] for row in cursor.fetchall()}

            for name in sorted(REQUIRED_TRIGGERS - triggers):
                issues.append(SchemaContractIssue(f'В базе отсутствует trigger {name}.'))
            for name in sorted(REQUIRED_FUNCTIONS - functions):
                issues.append(SchemaContractIssue(f'В базе отсутствует function {name}.'))

    return issues
