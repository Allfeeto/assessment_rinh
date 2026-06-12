from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Competence(models.Model):
    id = models.AutoField(primary_key=True)
    educational_program = models.ForeignKey(
        'programs.EducationalProgram',
        on_delete=models.CASCADE,
        db_column='educational_program_id',
        related_name='competences',
        verbose_name='Образовательная программа',
    )
    competence_type = models.ForeignKey(
        'core.CompetenceType',
        on_delete=models.PROTECT,
        db_column='competence_type_id',
        related_name='competences',
        verbose_name='Тип компетенции',
    )
    code = models.TextField(verbose_name='Код компетенции')
    name = models.TextField(verbose_name='Наименование компетенции')

    class Meta:
        managed = False
        db_table = 'competence'
        verbose_name = 'Компетенция'
        verbose_name_plural = 'Компетенции'
        constraints = [
            models.UniqueConstraint(
                fields=('educational_program', 'code'),
                name='competence_educational_program_id_code_key',
            )
        ]

    def __str__(self):
        return f'{self.code} — {self.name}'


class DisciplineCompetence(models.Model):
    id = models.AutoField(primary_key=True)
    program_discipline = models.ForeignKey(
        'disciplines.ProgramDiscipline',
        on_delete=models.CASCADE,
        db_column='program_discipline_id',
        related_name='discipline_competences',
        verbose_name='Дисциплина учебного плана',
    )
    competence = models.ForeignKey(
        Competence,
        on_delete=models.CASCADE,
        db_column='competence_id',
        related_name='discipline_competences',
        verbose_name='Компетенция',
    )

    class Meta:
        managed = False
        db_table = 'discipline_competence'
        verbose_name = 'Связь дисциплины и компетенции'
        verbose_name_plural = 'Связи дисциплин и компетенций'
        constraints = [
            models.UniqueConstraint(
                fields=('program_discipline', 'competence'),
                name='discipline_competence_program_discipline_id_competence_id_key',
            )
        ]

    def __str__(self):
        return f'{self.program_discipline} -> {self.competence.code}'

    def clean(self):
        super().clean()
        if not self.program_discipline_id or not self.competence_id:
            return

        from disciplines.models import ProgramDiscipline

        program_discipline_program_id = getattr(
            getattr(self, 'program_discipline', None),
            'educational_program_id',
            None,
        )
        if program_discipline_program_id is None:
            program_discipline_program_id = (
                ProgramDiscipline.objects.filter(pk=self.program_discipline_id)
                .values_list('educational_program_id', flat=True)
                .first()
            )

        competence_program_id = getattr(
            getattr(self, 'competence', None),
            'educational_program_id',
            None,
        )
        if competence_program_id is None:
            competence_program_id = (
                Competence.objects.filter(pk=self.competence_id)
                .values_list('educational_program_id', flat=True)
                .first()
            )

        if (
            program_discipline_program_id is not None
            and competence_program_id is not None
            and program_discipline_program_id != competence_program_id
        ):
            raise ValidationError({
                'competence': 'Дисциплина учебного плана и компетенция должны относиться к одной программе.'
            })


class CompetenceIndicatorImport(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'processing', 'Выполняется'
        COMPLETED = 'completed', 'Завершён'
        FAILED = 'failed', 'Ошибка'

    id = models.AutoField(primary_key=True)
    educational_program = models.ForeignKey(
        'programs.EducationalProgram',
        on_delete=models.CASCADE,
        db_column='educational_program_id',
        related_name='competence_indicator_imports',
        verbose_name='Образовательная программа',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column='uploaded_by_id',
        related_name='competence_indicator_imports',
        blank=True,
        null=True,
        verbose_name='Кто загрузил',
    )
    source_filename = models.CharField(max_length=255, verbose_name='Имя файла')
    source_sha256 = models.CharField(max_length=64, verbose_name='SHA-256 файла')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
        verbose_name='Статус',
    )
    total_rows = models.PositiveIntegerField(default=0, verbose_name='Найдено индикаторов')
    created_count = models.PositiveIntegerField(default=0, verbose_name='Создано')
    updated_count = models.PositiveIntegerField(default=0, verbose_name='Обновлено')
    skipped_count = models.PositiveIntegerField(default=0, verbose_name='Пропущено')
    error_count = models.PositiveIntegerField(default=0, verbose_name='Ошибок')
    warning_count = models.PositiveIntegerField(default=0, verbose_name='Предупреждений')
    error_summary = models.TextField(blank=True, null=True, verbose_name='Отчёт об ошибках')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='Завершён')

    class Meta:
        managed = False
        db_table = 'competence_indicator_import'
        verbose_name = 'Импорт индикаторов компетенций'
        verbose_name_plural = 'Импорты индикаторов компетенций'
        indexes = [
            models.Index(
                fields=('educational_program', 'created_at'),
                name='comp_ind_imp_prog_date_idx',
            ),
            models.Index(fields=('status',), name='comp_ind_imp_status_idx'),
            models.Index(fields=('source_sha256',), name='comp_ind_imp_sha_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=('processing', 'completed', 'failed')),
                name='competence_indicator_import_status_check',
            ),
            models.CheckConstraint(
                condition=Q(
                    total_rows__gte=0,
                    created_count__gte=0,
                    updated_count__gte=0,
                    skipped_count__gte=0,
                    error_count__gte=0,
                    warning_count__gte=0,
                ),
                name='competence_indicator_import_counts_check',
            ),
        ]

    def __str__(self):
        return f'{self.source_filename} — {self.get_status_display()}'


class CompetenceIndicator(models.Model):
    id = models.AutoField(primary_key=True)
    competence = models.ForeignKey(
        Competence,
        on_delete=models.CASCADE,
        db_column='competence_id',
        related_name='indicators',
        verbose_name='Компетенция',
    )
    last_import = models.ForeignKey(
        CompetenceIndicatorImport,
        on_delete=models.SET_NULL,
        db_column='last_import_id',
        related_name='last_imported_indicators',
        blank=True,
        null=True,
        verbose_name='Последний импорт',
    )
    code = models.CharField(max_length=50, verbose_name='Код индикатора')
    text = models.TextField(verbose_name='Текст индикатора')
    source_file = models.CharField(max_length=255, verbose_name='Файл-источник')
    source_table_number = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Номер таблицы в файле',
    )
    source_row_number = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Номер строки таблицы',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')

    class Meta:
        managed = False
        db_table = 'competence_indicator'
        verbose_name = 'Индикатор достижения компетенции'
        verbose_name_plural = 'Индикаторы достижения компетенций'
        constraints = [
            models.UniqueConstraint(
                fields=('competence', 'code'),
                name='competence_indicator_competence_code_key',
            ),
            models.CheckConstraint(
                condition=Q(source_table_number__isnull=True) | Q(source_table_number__gt=0),
                name='competence_indicator_source_table_check',
            ),
            models.CheckConstraint(
                condition=Q(source_row_number__isnull=True) | Q(source_row_number__gt=0),
                name='competence_indicator_source_row_check',
            ),
        ]
        indexes = [
            models.Index(fields=('competence',), name='comp_indicator_competence_idx'),
            models.Index(fields=('code',), name='comp_indicator_code_idx'),
        ]

    def __str__(self):
        return f'{self.code} — {self.text[:80]}'
