from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


MIN_ADMISSION_YEAR = 2000
MAX_ADMISSION_YEAR = 2100


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

    def clean(self):
        super().clean()
        code = (self.code or '').strip()
        direction = getattr(self, 'training_direction', None)
        direction_code = (getattr(direction, 'code', '') or '').strip()
        if not direction_code and self.training_direction_id:
            direction_code = (
                TrainingDirection.objects.filter(pk=self.training_direction_id)
                .values_list('code', flat=True)
                .first()
                or ''
            ).strip()

        if direction_code and code and not code.startswith(f'{direction_code}.'):
            raise ValidationError({
                'code': f'Код профиля должен начинаться с кода направления "{direction_code}.".'
            })


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
    admission_year = models.SmallIntegerField(
        validators=[
            MinValueValidator(MIN_ADMISSION_YEAR),
            MaxValueValidator(MAX_ADMISSION_YEAR),
        ],
        verbose_name='Год набора',
    )
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
            models.CheckConstraint(
                condition=Q(admission_year__gte=MIN_ADMISSION_YEAR)
                & Q(admission_year__lte=MAX_ADMISSION_YEAR),
                name='educational_program_admission_year_check',
            ),
            models.UniqueConstraint(
                fields=('program_profile', 'department', 'admission_year'),
                condition=Q(is_deleted=False),
                name='educational_program_active_unique_idx',
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.admission_year is not None and not (
            MIN_ADMISSION_YEAR <= self.admission_year <= MAX_ADMISSION_YEAR
        ):
            errors['admission_year'] = (
                f'Год набора должен быть в диапазоне {MIN_ADMISSION_YEAR}-{MAX_ADMISSION_YEAR}.'
            )

        if (
            self.program_profile_id
            and self.department_id
            and self.admission_year is not None
            and not self.is_deleted
        ):
            duplicate = self.__class__.objects.active().filter(
                program_profile_id=self.program_profile_id,
                department_id=self.department_id,
                admission_year=self.admission_year,
            )
            if self.pk:
                duplicate = duplicate.exclude(pk=self.pk)
            if duplicate.exists():
                errors['admission_year'] = (
                    'Активная образовательная программа с таким профилем, кафедрой '
                    'и годом набора уже существует.'
                )

        if errors:
            raise ValidationError(errors)

    @property
    def base_name(self):
        return (
            f'{self.program_profile.code} | {self.department.short_name} | '
            f'набор {self.admission_year}'
        )

    @property
    def full_display_name(self):
        profile = getattr(self, 'program_profile', None)
        department = getattr(self, 'department', None)
        direction = getattr(profile, 'training_direction', None)
        education_level = getattr(direction, 'education_level', None)

        code = (getattr(profile, 'code', '') or '').strip()
        name = (getattr(profile, 'name', '') or '').strip()
        if code and name:
            label = f'{code} — {name}'
        else:
            label = code or name or 'Образовательная программа'

        details = []
        if self.admission_year:
            details.append(f'набор {self.admission_year}')
        department_short_name = (getattr(department, 'short_name', '') or '').strip()
        if department_short_name:
            details.append(department_short_name)
        education_level_name = (getattr(education_level, 'name', '') or '').strip()
        if education_level_name:
            details.append(education_level_name)
        if details:
            label = f'{label}, {", ".join(details)}'
        if self.is_deleted:
            label = f'{label} (в корзине)'
        return label

    @property
    def display_name(self):
        label = self.base_name
        if self.is_deleted and '(в корзине)' not in label:
            return f'{label} (в корзине)'
        return label

    def __str__(self):
        return self.display_name
