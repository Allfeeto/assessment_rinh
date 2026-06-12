from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('teachers', '0001_teacher_departments'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainingDirection',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='Код направления')),
                ('name', models.TextField(verbose_name='Наименование направления')),
                ('education_level', models.ForeignKey(db_column='education_level_id', on_delete=django.db.models.deletion.PROTECT, related_name='training_directions', to='core.educationlevel', verbose_name='Уровень образования')),
            ],
            options={
                'verbose_name': 'Направление подготовки',
                'verbose_name_plural': 'Направления подготовки',
                'db_table': 'training_direction',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ProgramProfile',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=30, unique=True, verbose_name='Код профиля')),
                ('name', models.TextField(verbose_name='Наименование профиля')),
                ('training_direction', models.ForeignKey(db_column='training_direction_id', on_delete=django.db.models.deletion.CASCADE, related_name='program_profiles', to='programs.trainingdirection', verbose_name='Направление подготовки')),
            ],
            options={
                'verbose_name': 'Профиль программы',
                'verbose_name_plural': 'Профили программ',
                'db_table': 'program_profile',
                'managed': False,
                'constraints': [
                    models.UniqueConstraint(fields=('training_direction', 'name'), name='program_profile_training_direction_id_name_key'),
                ],
            },
        ),
        migrations.CreateModel(
            name='EducationalProgram',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('admission_year', models.SmallIntegerField(verbose_name='Год набора')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='В корзине')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата перемещения в корзину')),
                ('delete_reason', models.TextField(blank=True, null=True, verbose_name='Причина перемещения в корзину')),
                ('deleted_by', models.ForeignKey(blank=True, db_column='deleted_by_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_educational_programs', to=settings.AUTH_USER_MODEL, verbose_name='Кто переместил в корзину')),
                ('department', models.ForeignKey(db_column='department_id', on_delete=django.db.models.deletion.PROTECT, related_name='educational_programs', to='teachers.department', verbose_name='Кафедра')),
                ('program_profile', models.ForeignKey(db_column='program_profile_id', on_delete=django.db.models.deletion.PROTECT, related_name='educational_programs', to='programs.programprofile', verbose_name='Профиль')),
            ],
            options={
                'verbose_name': 'Образовательная программа',
                'verbose_name_plural': 'Образовательные программы',
                'db_table': 'educational_program',
                'managed': False,
                'constraints': [
                    models.CheckConstraint(condition=models.Q(('admission_year__gte', 2000), ('admission_year__lte', 2100)), name='educational_program_admission_year_check'),
                    models.UniqueConstraint(condition=models.Q(('is_deleted', False)), fields=('program_profile', 'department', 'admission_year'), name='educational_program_active_unique_idx'),
                ],
            },
        ),
    ]
