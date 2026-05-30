from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('disciplines', '0001_program_discipline_plx_fields'),
        ('teachers', '0001_teacher_departments'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeacherProgramDiscipline',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('program_discipline', models.ForeignKey(db_column='program_discipline_id', on_delete=django.db.models.deletion.CASCADE, related_name='teacher_program_disciplines', to='disciplines.programdiscipline', verbose_name='Дисциплина учебного плана')),
                ('teacher', models.ForeignKey(db_column='teacher_id', on_delete=django.db.models.deletion.CASCADE, related_name='teacher_program_disciplines', to='teachers.teacher', verbose_name='Преподаватель')),
            ],
            options={
                'verbose_name': 'Привязка преподавателя к дисциплине учебного плана',
                'verbose_name_plural': 'Привязки преподавателей к дисциплинам учебных планов',
                'db_table': 'teacher_program_discipline',
                'managed': False,
                'constraints': [models.UniqueConstraint(fields=('teacher', 'program_discipline'), name='teacher_program_discipline_teacher_id_program_discipline_id_key')],
            },
        ),
    ]
