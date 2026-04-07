from django.db import models


class AssessmentItem(models.Model):
    id = models.AutoField(primary_key=True)
    program_discipline = models.ForeignKey(
        'disciplines.ProgramDiscipline',
        on_delete=models.CASCADE,
        db_column='program_discipline_id',
        related_name='assessment_items',
        verbose_name='Дисциплина учебного плана',
    )
    assessment_item_type = models.ForeignKey(
        'core.AssessmentItemType',
        on_delete=models.PROTECT,
        db_column='assessment_item_type_id',
        related_name='assessment_items',
        verbose_name='Тип задания',
    )
    prompt_text = models.TextField(verbose_name='Текст задания')
    instruction_text = models.TextField(blank=True, null=True, verbose_name='Инструкция')
    left_column_title = models.TextField(blank=True, null=True, verbose_name='Заголовок левой колонки')
    right_column_title = models.TextField(blank=True, null=True, verbose_name='Заголовок правой колонки')

    class Meta:
        managed = False
        db_table = 'assessment_item'
        verbose_name = 'Оценочное задание'
        verbose_name_plural = 'Оценочные задания'

    def __str__(self):
        return f'#{self.id} {self.prompt_text[:80]}'


class AssessmentItemCompetence(models.Model):
    assessment_item = models.OneToOneField(
        AssessmentItem,
        on_delete=models.CASCADE,
        db_column='assessment_item_id',
        related_name='assessment_item_competence_link',
        primary_key=True,
        verbose_name='Задание',
    )
    competence = models.ForeignKey(
        'competencies.Competence',
        on_delete=models.CASCADE,
        db_column='competence_id',
        related_name='assessment_item_links',
        verbose_name='Компетенция',
    )

    class Meta:
        managed = False
        db_table = 'assessment_item_competence'
        verbose_name = 'Связь задания с компетенцией'
        verbose_name_plural = 'Связи заданий с компетенциями'
        constraints = [
            models.UniqueConstraint(
                fields=('assessment_item', 'competence'),
                name='assessment_item_competence_pkey',
            )
        ]

    def __str__(self):
        return f'{self.assessment_item_id} -> {self.competence_id}'


class AssessmentItemRow(models.Model):
    KIND_OPTION = 'option'
    KIND_MATCH_PAIR = 'match_pair'
    KIND_MATCH_RIGHT_DISTRACTOR = 'match_right_distractor'
    KIND_SEQUENCE = 'sequence'
    KIND_OPEN_ANSWER = 'open_answer'

    ROW_KIND_CHOICES = (
        (KIND_OPTION, 'Вариант ответа'),
        (KIND_MATCH_PAIR, 'Пара соответствия'),
        (KIND_MATCH_RIGHT_DISTRACTOR, 'Дистрактор правой колонки'),
        (KIND_SEQUENCE, 'Элемент последовательности'),
        (KIND_OPEN_ANSWER, 'Допустимый открытый ответ'),
    )

    id = models.AutoField(primary_key=True)
    assessment_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.CASCADE,
        db_column='assessment_item_id',
        related_name='rows',
        verbose_name='Задание',
    )
    row_kind = models.CharField(max_length=30, choices=ROW_KIND_CHOICES, verbose_name='Тип строки')
    left_label = models.TextField(blank=True, null=True, verbose_name='Левая метка')
    right_label = models.TextField(blank=True, null=True, verbose_name='Правая метка')
    left_text = models.TextField(blank=True, null=True, verbose_name='Левый текст')
    right_text = models.TextField(blank=True, null=True, verbose_name='Правый текст')
    sort_order = models.IntegerField(blank=True, null=True, verbose_name='Порядок отображения')
    correct_order = models.IntegerField(blank=True, null=True, verbose_name='Верный порядок')
    is_correct = models.BooleanField(blank=True, null=True, verbose_name='Правильный')
    open_answer_text = models.TextField(blank=True, null=True, verbose_name='Допустимый ответ')

    class Meta:
        managed = False
        db_table = 'assessment_item_row'
        verbose_name = 'Строка задания'
        verbose_name_plural = 'Строки задания'

    def __str__(self):
        return f'{self.get_row_kind_display()} #{self.id}'