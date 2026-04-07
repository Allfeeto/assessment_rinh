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

    def __str__(self):
        return f'{self.educational_program} | {self.discipline.name}'