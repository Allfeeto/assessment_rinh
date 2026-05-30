from django.db import migrations, models
import django.db.models.deletion


def apply_program_discipline_schema(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE public.program_discipline
                ADD COLUMN IF NOT EXISTS discipline_code character varying(50);
            ALTER TABLE public.program_discipline
                ADD COLUMN IF NOT EXISTS department_id integer;

            DO $$
            BEGIN
                ALTER TABLE public.program_discipline
                    ADD CONSTRAINT program_discipline_department_id_fk
                    FOREIGN KEY (department_id)
                    REFERENCES public.department(id)
                    DEFERRABLE INITIALLY DEFERRED;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;

            CREATE INDEX IF NOT EXISTS program_disc_code_idx
                ON public.program_discipline (discipline_code);
            CREATE INDEX IF NOT EXISTS program_disc_dept_idx
                ON public.program_discipline (department_id);
            CREATE INDEX IF NOT EXISTS program_disc_prog_code_idx
                ON public.program_discipline (educational_program_id, discipline_code);
            """
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('teachers', '0001_teacher_departments'),
    ]

    operations = [
        migrations.CreateModel(
            name='Discipline',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.TextField(unique=True, verbose_name='Наименование дисциплины')),
            ],
            options={
                'verbose_name': 'Дисциплина',
                'verbose_name_plural': 'Дисциплины',
                'db_table': 'discipline',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ProgramDiscipline',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('discipline_code', models.CharField(blank=True, help_text='Код позиции дисциплины внутри конкретной образовательной программы, например Б1.О.07.', max_length=50, null=True, verbose_name='Код дисциплины в учебном плане')),
                ('department', models.ForeignKey(blank=True, db_column='department_id', help_text='Кафедра, указанная для строки учебного плана в PLX.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='discipline_program_disciplines', to='teachers.department', verbose_name='Кафедра дисциплины')),
                ('discipline', models.ForeignKey(db_column='discipline_id', on_delete=django.db.models.deletion.PROTECT, related_name='program_disciplines', to='disciplines.discipline', verbose_name='Дисциплина')),
                ('educational_program', models.ForeignKey(db_column='educational_program_id', on_delete=django.db.models.deletion.CASCADE, related_name='program_disciplines', to='programs.educationalprogram', verbose_name='Образовательная программа')),
            ],
            options={
                'verbose_name': 'Дисциплина учебного плана',
                'verbose_name_plural': 'Дисциплины учебных планов',
                'db_table': 'program_discipline',
                'managed': False,
                'indexes': [
                    models.Index(fields=['discipline_code'], name='program_disc_code_idx'),
                    models.Index(fields=['department'], name='program_disc_dept_idx'),
                    models.Index(fields=['educational_program', 'discipline_code'], name='program_disc_prog_code_idx'),
                ],
                'constraints': [models.UniqueConstraint(fields=('educational_program', 'discipline'), name='program_discipline_educational_program_id_discipline_id_key')],
            },
        ),
        migrations.RunPython(
            apply_program_discipline_schema,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
