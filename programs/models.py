from django.conf import settings
from django.db import models
from django.db.models import Q


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


class EducationalProgramQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)

    def in_trash(self):
        return self.filter(is_deleted=True)

    def with_trash(self):
        return self


class EducationalProgramManager(models.Manager.from_queryset(EducationalProgramQuerySet)):
    pass


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
    is_deleted = models.BooleanField(default=False, verbose_name='В корзине')
    deleted_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата перемещения в корзину')
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column='deleted_by_id',
        related_name='deleted_educational_programs',
        blank=True,
        null=True,
        verbose_name='Кто переместил в корзину',
    )
    delete_reason = models.TextField(blank=True, null=True, verbose_name='Причина перемещения в корзину')

    objects = EducationalProgramManager()

    class Meta:
        managed = False
        db_table = 'educational_program'
        verbose_name = 'Образовательная программа'
        verbose_name_plural = 'Образовательные программы'
        constraints = [
            models.UniqueConstraint(
                fields=('program_profile', 'department', 'admission_year'),
                condition=Q(is_deleted=False),
                name='educational_program_active_unique_idx',
            )
        ]

    @property
    def base_name(self):
        return (
            f'{self.program_profile.code} | {self.department.short_name} | '
            f'набор {self.admission_year}'
        )

    @property
    def display_name(self):
        label = self.base_name
        if self.is_deleted and '(в корзине)' not in label:
            return f'{label} (в корзине)'
        return label

    def __str__(self):
        return self.display_name
