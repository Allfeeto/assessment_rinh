from django.core.exceptions import ValidationError
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
