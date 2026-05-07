import os

import pytest
from django.db import connection


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(autouse=True)
def require_postgres_integration_db():
    if os.environ.get('RUN_POSTGRES_INTEGRATION_TESTS') != '1':
        pytest.skip('Set RUN_POSTGRES_INTEGRATION_TESTS=1 to run PostgreSQL invariant checks.')
    if connection.vendor != 'postgresql':
        pytest.skip('PostgreSQL invariant checks require a PostgreSQL database.')


def test_assessment_item_integrity_trigger_is_installed():
    required_functions = {
        'check_assessment_item_relation_integrity',
        'check_assessment_item_competence_relation_integrity',
        'check_assessment_item_row_by_type',
        'check_discipline_competence_same_program',
        'check_program_profile_code_prefix',
    }
    required_triggers = {
        'trg_check_assessment_item_relation_integrity',
        'trg_check_assessment_item_competence_relation_integrity',
        'trg_check_assessment_item_row_by_type',
        'trg_check_discipline_competence_same_program',
        'trg_check_program_profile_code_prefix',
    }
    required_constraints_or_indexes = {
        'educational_program_admission_year_check',
        'educational_program_active_unique_idx',
        'uq_assessment_item_row_correct_order',
        'uq_assessment_item_row_sort',
    }

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT proname
            FROM pg_proc
            WHERE proname = ANY(%s)
            """,
            [list(required_functions)],
        )
        functions = {row[0] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT tgname
            FROM pg_trigger
            WHERE tgname = ANY(%s)
              AND NOT tgisinternal
            """,
            [list(required_triggers)],
        )
        triggers = {row[0] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conname = ANY(%s)
            UNION
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = ANY(%s)
            """,
            [list(required_constraints_or_indexes), list(required_constraints_or_indexes)],
        )
        constraints_or_indexes = {row[0] for row in cursor.fetchall()}

    assert functions == required_functions
    assert triggers == required_triggers
    assert constraints_or_indexes == required_constraints_or_indexes
