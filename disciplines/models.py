from django.db import models


class Discipline(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(verbose_name='Наименование дисциплины')

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
        'core.EducationalProgram',
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

    class Meta:
        managed = False
        db_table = 'program_discipline'
        verbose_name = 'Дисциплина программы'
        verbose_name_plural = 'Дисциплины программ'
        unique_together = (('educational_program', 'discipline'),)

    def __str__(self):
        return f'{self.educational_program.code} / {self.discipline.name}'