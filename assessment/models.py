from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from .services import get_item_type_ui_name


class AssessmentItem(models.Model):
    id = models.AutoField(primary_key=True)
    program_discipline = models.ForeignKey(
        'disciplines.ProgramDiscipline',
        on_delete=models.CASCADE,
        db_column='program_discipline_id',
        related_name='assessment_items',
        verbose_name='Дисциплина учебного плана',
    )
    competence = models.ForeignKey(
        'competencies.Competence',
        on_delete=models.PROTECT,
        db_column='competence_id',
        related_name='assessment_items',
        null=True,
        blank=True,
        verbose_name='Компетенция',
        help_text='Legacy FK: canonical links are stored in AssessmentItemCompetence.',
    )
    assessment_item_type = models.ForeignKey(
        'core.AssessmentItemType',
        on_delete=models.PROTECT,
        db_column='assessment_item_type_id',
        related_name='assessment_items',
        verbose_name='Тип задания',
    )
    prompt_text = models.TextField(verbose_name='Текст задания')
    left_column_title = models.TextField(blank=True, null=True, verbose_name='Заголовок левой колонки')
    right_column_title = models.TextField(blank=True, null=True, verbose_name='Заголовок правой колонки')

    class Meta:
        managed = False
        db_table = 'assessment_item'
        verbose_name = 'Оценочное задание'
        verbose_name_plural = 'Оценочные задания'

    def __str__(self):
        return f'#{self.id} {self.prompt_text[:80]}'

    def clean(self):
        super().clean()
        if not self.competence_id or not self.program_discipline_id:
            return

        from competencies.models import Competence, DisciplineCompetence
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
                'competence': (
                    'Дисциплина учебного плана и компетенция задания должны относиться '
                    'к одной образовательной программе.'
                )
            })

        if not DisciplineCompetence.objects.filter(
            program_discipline_id=self.program_discipline_id,
            competence_id=self.competence_id,
        ).exists():
            raise ValidationError({
                'competence': (
                    'Для выбранной дисциплины учебного плана нет связи с этой компетенцией '
                    'в матрице дисциплина-компетенция.'
                )
            })

    @property
    def item_type_ui_name(self):
        override = getattr(self, '_item_type_ui_name_override', None)
        if override:
            return override
        return get_item_type_ui_name(self.assessment_item_type)

    @item_type_ui_name.setter
    def item_type_ui_name(self, value):
        self._item_type_ui_name_override = value


class AssessmentItemRow(models.Model):
    id = models.AutoField(primary_key=True)
    assessment_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.CASCADE,
        db_column='assessment_item_id',
        related_name='rows',
        verbose_name='Задание',
    )
    left_text = models.TextField(blank=True, null=True, verbose_name='Левый текст')
    right_text = models.TextField(blank=True, null=True, verbose_name='Правый текст')
    sort_order = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        verbose_name='Порядок отображения',
    )
    correct_order = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        verbose_name='Верный порядок',
    )
    is_correct = models.BooleanField(blank=True, null=True, verbose_name='Верный вариант')
    open_answer_text = models.TextField(blank=True, null=True, verbose_name='Допустимый ответ')

    class Meta:
        managed = False
        db_table = 'assessment_item_row'
        verbose_name = 'Строка задания'
        verbose_name_plural = 'Строки задания'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(sort_order__isnull=True) | models.Q(sort_order__gt=0),
                name='assessment_item_row_sort_order_check',
            ),
            models.CheckConstraint(
                condition=models.Q(correct_order__isnull=True) | models.Q(correct_order__gt=0),
                name='assessment_item_row_correct_order_check',
            ),
            models.UniqueConstraint(
                fields=('assessment_item', 'sort_order'),
                condition=models.Q(sort_order__isnull=False),
                name='uq_assessment_item_row_sort',
            ),
            models.UniqueConstraint(
                fields=('assessment_item', 'correct_order'),
                condition=models.Q(correct_order__isnull=False),
                name='uq_assessment_item_row_correct_order',
            ),
        ]

    def __str__(self):
        return f'Строка #{self.id} задания #{self.assessment_item_id}'


class AssessmentItemCompetence(models.Model):
    id = models.AutoField(primary_key=True)
    assessment_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.CASCADE,
        db_column='assessment_item_id',
        related_name='competence_links',
        verbose_name='Задание',
    )
    competence = models.ForeignKey(
        'competencies.Competence',
        on_delete=models.PROTECT,
        db_column='competence_id',
        related_name='assessment_item_links',
        verbose_name='Компетенция',
    )

    class Meta:
        managed = False
        db_table = 'assessment_item_competence'
        verbose_name = 'Связь задания и компетенции'
        verbose_name_plural = 'Связи заданий и компетенций'
        constraints = [
            models.UniqueConstraint(
                fields=('assessment_item', 'competence'),
                name='assessment_item_competence_assessment_item_id_competence_id_key',
            )
        ]

    def __str__(self):
        return f'Задание #{self.assessment_item_id} -> {self.competence.code}'

    def clean(self):
        super().clean()
        if not self.assessment_item_id or not self.competence_id:
            return

        from competencies.models import Competence, DisciplineCompetence

        item = getattr(self, 'assessment_item', None)
        item_program_discipline_id = getattr(item, 'program_discipline_id', None)
        item_program_id = getattr(
            getattr(item, 'program_discipline', None),
            'educational_program_id',
            None,
        )
        if item_program_discipline_id is None or item_program_id is None:
            item = (
                AssessmentItem.objects.filter(pk=self.assessment_item_id)
                .select_related('program_discipline')
                .first()
            )
            item_program_discipline_id = getattr(item, 'program_discipline_id', None)
            item_program_id = getattr(
                getattr(item, 'program_discipline', None),
                'educational_program_id',
                None,
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

        if item_program_id is not None and competence_program_id is not None and item_program_id != competence_program_id:
            raise ValidationError({
                'competence': 'Задание и компетенция должны относиться к одной образовательной программе.'
            })

        if item_program_discipline_id and not DisciplineCompetence.objects.filter(
            program_discipline_id=item_program_discipline_id,
            competence_id=self.competence_id,
        ).exists():
            raise ValidationError({
                'competence': (
                    'Компетенция задания должна быть связана с дисциплиной учебного плана '
                    'в матрице дисциплина-компетенция.'
                )
            })
