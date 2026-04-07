from django.db import connection

from competencies.models import Competence


def get_assessment_item_competence_ids(assessment_item_id):
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT competence_id FROM assessment_item_competence WHERE assessment_item_id = %s ORDER BY competence_id',
            [assessment_item_id],
        )
        return [row[0] for row in cursor.fetchall()]


def get_competences_for_item(assessment_item_id):
    competence_ids = get_assessment_item_competence_ids(assessment_item_id)
    return list(Competence.objects.filter(id__in=competence_ids).order_by('code'))


def sync_assessment_item_competences(assessment_item_id, competence_ids):
    unique_ids = sorted(set(competence_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            'DELETE FROM assessment_item_competence WHERE assessment_item_id = %s',
            [assessment_item_id],
        )
        if unique_ids:
            cursor.executemany(
                'INSERT INTO assessment_item_competence (assessment_item_id, competence_id) VALUES (%s, %s)',
                [(assessment_item_id, competence_id) for competence_id in unique_ids],
            )