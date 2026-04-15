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
        verbose_name='Компетенция',
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

    @property
    def item_type_ui_name(self):
        override = getattr(self, '_item_type_ui_name_override', None)
        if override:
            return override
        return get_item_type_ui_name(self.assessment_item_type.name)

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
    sort_order = models.IntegerField(blank=True, null=True, verbose_name='Порядок отображения')
    correct_order = models.IntegerField(blank=True, null=True, verbose_name='Верный порядок')
    is_correct = models.BooleanField(blank=True, null=True, verbose_name='Верный вариант')
    open_answer_text = models.TextField(blank=True, null=True, verbose_name='Допустимый ответ')

    class Meta:
        managed = False
        db_table = 'assessment_item_row'
        verbose_name = 'Строка задания'
        verbose_name_plural = 'Строки задания'

    def __str__(self):
        return f'Строка #{self.id} задания #{self.assessment_item_id}'
