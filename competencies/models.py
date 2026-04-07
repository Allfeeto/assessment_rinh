from django.db import models


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