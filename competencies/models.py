from django.db import models


class CompetenceType(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, verbose_name='Наименование типа')

    class Meta:
        managed = False
        db_table = 'competence_type'
        verbose_name = 'Тип компетенции'
        verbose_name_plural = 'Типы компетенций'

    def __str__(self):
        return self.name


class Competence(models.Model):
    id = models.AutoField(primary_key=True)
    educational_program = models.ForeignKey(
        'core.EducationalProgram',
        on_delete=models.CASCADE,
        db_column='educational_program_id',
        related_name='competences',
        verbose_name='Образовательная программа',
    )
    competence_type = models.ForeignKey(
        CompetenceType,
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
        unique_together = (('educational_program', 'code'),)

    def __str__(self):
        return f'{self.code} {self.name}'


class DisciplineCompetence(models.Model):
    id = models.AutoField(primary_key=True)
    program_discipline = models.ForeignKey(
        'disciplines.ProgramDiscipline',
        on_delete=models.CASCADE,
        db_column='program_discipline_id',
        related_name='discipline_competences',
        verbose_name='Дисциплина программы',
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
        unique_together = (('program_discipline', 'competence'),)

    def __str__(self):
        return f'{self.program_discipline} -> {self.competence.code}'