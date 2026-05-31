from django.db import migrations, models


def apply_program_discipline_active_schema(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE public.program_discipline
                ADD COLUMN IF NOT EXISTS is_active_in_plan boolean NOT NULL DEFAULT true;
            CREATE INDEX IF NOT EXISTS program_disc_prog_active_idx
                ON public.program_discipline (educational_program_id, is_active_in_plan);
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ('disciplines', '0001_program_discipline_plx_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='programdiscipline',
            name='is_active_in_plan',
            field=models.BooleanField(
                default=True,
                help_text='Сбрасывается при обновлении PLX, если строка больше не найдена в новом учебном плане.',
                verbose_name='Есть в актуальном учебном плане',
            ),
        ),
        migrations.AddIndex(
            model_name='programdiscipline',
            index=models.Index(
                fields=['educational_program', 'is_active_in_plan'],
                name='program_disc_prog_active_idx',
            ),
        ),
        migrations.RunPython(
            apply_program_discipline_active_schema,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
