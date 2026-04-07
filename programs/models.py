from django.db import models


class TrainingDirection(models.Model):
    id = models.AutoField(primary_key=True)
    education_level = models.ForeignKey(
        'core.EducationLevel',
        on_delete=models.PROTECT,
        db_column='education_level_id',
        related_name='training_directions',
        verbose_name='Уровень образования',
    )
    code = models.CharField(max_length=20, unique=True, verbose_name='Код направления')
    name = models.TextField(verbose_name='Наименование направления')

    class Meta:
        managed = False
        db_table = 'training_direction'
        verbose_name = 'Направление подготовки'
        verbose_name_plural = 'Направления подготовки'

    def __str__(self):
        return f'{self.code} — {self.name}'


class ProgramProfile(models.Model):
    id = models.AutoField(primary_key=True)
    training_direction = models.ForeignKey(
        TrainingDirection,
        on_delete=models.CASCADE,
        db_column='training_direction_id',
        related_name='program_profiles',
        verbose_name='Направление подготовки',
    )
    code = models.CharField(max_length=30, unique=True, verbose_name='Код профиля')
    name = models.TextField(verbose_name='Наименование профиля')

    class Meta:
        managed = False
        db_table = 'program_profile'
        verbose_name = 'Профиль программы'
        verbose_name_plural = 'Профили программ'
        constraints = [
            models.UniqueConstraint(
                fields=('training_direction', 'name'),
                name='program_profile_training_direction_id_name_key',
            )
        ]

    def __str__(self):
        return f'{self.code} — {self.name}'


class EducationalProgram(models.Model):
    id = models.AutoField(primary_key=True)
    program_profile = models.ForeignKey(
        ProgramProfile,
        on_delete=models.PROTECT,
        db_column='program_profile_id',
        related_name='educational_programs',
        verbose_name='Профиль',
    )
    department = models.ForeignKey(
        'teachers.Department',
        on_delete=models.PROTECT,
        db_column='department_id',
        related_name='educational_programs',
        verbose_name='Кафедра',
    )
    admission_year = models.SmallIntegerField(verbose_name='Год набора')

    class Meta:
        managed = False
        db_table = 'educational_program'
        verbose_name = 'Образовательная программа'
        verbose_name_plural = 'Образовательные программы'
        constraints = [
            models.UniqueConstraint(
                fields=('program_profile', 'department', 'admission_year'),
                name='educational_program_program_profile_id_department_id_admission_key',
            )
        ]

    def __str__(self):
        return (
            f'{self.program_profile.code} | {self.department.short_name} | '
            f'набор {self.admission_year}'
        )