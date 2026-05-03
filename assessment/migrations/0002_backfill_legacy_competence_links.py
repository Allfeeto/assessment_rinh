from django.db import migrations


def backfill_legacy_competence_links(apps, schema_editor):
    connection = schema_editor.connection
    tables = set(connection.introspection.table_names())
    required_tables = {'assessment_item', 'assessment_item_competence'}
    if not required_tables.issubset(tables):
        return

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO assessment_item_competence (assessment_item_id, competence_id)
            SELECT ai.id, ai.competence_id
            FROM assessment_item ai
            WHERE ai.competence_id IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM discipline_competence dc
                  WHERE dc.program_discipline_id = ai.program_discipline_id
                    AND dc.competence_id = ai.competence_id
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM assessment_item_competence aic
                  WHERE aic.assessment_item_id = ai.id
                    AND aic.competence_id = ai.competence_id
              )
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ('assessment', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_legacy_competence_links, migrations.RunPython.noop),
    ]
