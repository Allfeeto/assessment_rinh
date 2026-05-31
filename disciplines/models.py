from django.db import models


class Discipline(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, verbose_name='Наименование дисциплины')

    class Meta:
        managed = False
        db_table = 'discipline'
        verbose_name = 'Дисциплина'
        verbose_name_plural = 'Дисциплины'

    def __str__(self):
        return self.name


class ProgramDiscipline(models.Model):
    id = models.AutoField(primary_key=True)
    educational_program = models.ForeignKey(
        'programs.EducationalProgram',
        on_delete=models.CASCADE,
        db_column='educational_program_id',
        related_name='program_disciplines',
        verbose_name='Образовательная программа',
    )
    discipline = models.ForeignKey(
        Discipline,
        on_delete=models.PROTECT,
        db_column='discipline_id',
        related_name='program_disciplines',
        verbose_name='Дисциплина',
    )
    discipline_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Код дисциплины в учебном плане',
        help_text='Код позиции дисциплины внутри конкретной образовательной программы, например Б1.О.07.',
    )
    department = models.ForeignKey(
        'teachers.Department',
        on_delete=models.PROTECT,
        db_column='department_id',
        related_name='discipline_program_disciplines',
        blank=True,
        null=True,
        verbose_name='Кафедра дисциплины',
        help_text='Кафедра, указанная для строки учебного плана в PLX.',
    )
    is_active_in_plan = models.BooleanField(
        default=True,
        verbose_name='Есть в актуальном учебном плане',
        help_text='Сбрасывается при обновлении PLX, если строка больше не найдена в новом учебном плане.',
    )

    class Meta:
        managed = False
        db_table = 'program_discipline'
        verbose_name = 'Дисциплина учебного плана'
        verbose_name_plural = 'Дисциплины учебных планов'
        constraints = [
            models.UniqueConstraint(
                fields=('educational_program', 'discipline'),
                name='program_discipline_educational_program_id_discipline_id_key',
            )
        ]
        indexes = [
            models.Index(fields=('discipline_code',), name='program_disc_code_idx'),
            models.Index(fields=('department',), name='program_disc_dept_idx'),
            models.Index(
                fields=('educational_program', 'discipline_code'),
                name='program_disc_prog_code_idx',
            ),
            models.Index(
                fields=('educational_program', 'is_active_in_plan'),
                name='program_disc_prog_active_idx',
            ),
        ]

    def __str__(self):
        return f'{self.educational_program} | {self.discipline_display_name}'

    @property
    def discipline_display_name(self):
        if self.discipline_code:
            return f'{self.discipline_code} — {self.discipline.name}'
        return self.discipline.name

    @property
    def plan_status_label(self):
        return 'В актуальном PLX' if self.is_active_in_plan else 'Нет в актуальном PLX'
