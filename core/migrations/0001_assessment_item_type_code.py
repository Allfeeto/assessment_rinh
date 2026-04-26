from django.db import migrations


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE public.assessment_item_type
                ADD COLUMN IF NOT EXISTS code character varying(20);

            WITH candidates AS (
                SELECT
                    id,
                    CASE
                        WHEN lower(coalesce(code, '')) IN ('single', 'single_choice')
                             OR lower(name) LIKE '%одного%'
                             OR lower(name) LIKE '%один%'
                            THEN 'single'
                        WHEN lower(coalesce(code, '')) IN ('multiple', 'multiple_choice')
                             OR lower(name) LIKE '%нескольк%'
                            THEN 'multiple'
                        WHEN lower(coalesce(code, '')) IN ('matching')
                             OR lower(name) LIKE '%соответств%'
                            THEN 'matching'
                        WHEN lower(coalesce(code, '')) IN ('sequence')
                             OR lower(name) LIKE '%последоват%'
                            THEN 'sequence'
                        WHEN lower(coalesce(code, '')) IN ('open', 'open_answer')
                             OR lower(name) LIKE '%открыт%'
                             OR lower(name) LIKE '%развернут%'
                            THEN 'open'
                        ELSE NULL
                    END AS desired_code
                FROM public.assessment_item_type
                WHERE code IS NULL
                   OR code = ''
                   OR lower(code) IN (
                        'single',
                        'multiple',
                        'matching',
                        'sequence',
                        'open',
                        'single_choice',
                        'multiple_choice',
                        'open_answer'
                   )
            ),
            ranked AS (
                SELECT
                    id,
                    desired_code,
                    ROW_NUMBER() OVER (PARTITION BY desired_code ORDER BY id) AS desired_rank
                FROM candidates
                WHERE desired_code IS NOT NULL
            )
            UPDATE public.assessment_item_type AS target
            SET code = CASE
                WHEN ranked.desired_rank = 1 THEN ranked.desired_code
                ELSE 'legacy_' || target.id::text
            END
            FROM ranked
            WHERE target.id = ranked.id;

            UPDATE public.assessment_item_type
            SET code = 'legacy_' || id::text
            WHERE code IS NULL OR code = '';

            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'assessment_item_type_code_key'
                      AND conrelid = 'public.assessment_item_type'::regclass
                ) THEN
                    ALTER TABLE public.assessment_item_type
                        ADD CONSTRAINT assessment_item_type_code_key UNIQUE (code);
                END IF;
            END
            $$;

            ALTER TABLE public.assessment_item_type
                ALTER COLUMN code SET NOT NULL;
            """,
            reverse_sql="""
            ALTER TABLE public.assessment_item_type
                DROP CONSTRAINT IF EXISTS assessment_item_type_code_key;
            ALTER TABLE public.assessment_item_type
                DROP COLUMN IF EXISTS code;
            """,
        ),
    ]
