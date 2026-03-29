from django.db import models


class AssessmentItemType(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, verbose_name='Наименование типа задания')

    class Meta:
        managed = False
        db_table = 'assessment_item_type'
        verbose_name = 'Тип задания'
        verbose_name_plural = 'Типы заданий'

    def __str__(self):
        return self.name


class AssessmentItem(models.Model):
    id = models.AutoField(primary_key=True)
    program_discipline = models.ForeignKey(
        'disciplines.ProgramDiscipline',
        on_delete=models.CASCADE,
        db_column='program_discipline_id',
        related_name='assessment_items',
        verbose_name='Дисциплина программы',
    )
    assessment_item_type = models.ForeignKey(
        AssessmentItemType,
        on_delete=models.PROTECT,
        db_column='assessment_item_type_id',
        related_name='assessment_items',
        verbose_name='Тип задания',
    )
    text = models.TextField(verbose_name='Текст задания')

    class Meta:
        managed = False
        db_table = 'assessment_item'
        verbose_name = 'Оценочное задание'
        verbose_name_plural = 'Оценочные задания'

    def __str__(self):
        return f'[{self.id}] {self.text[:70]}'


class AssessmentItemCompetence(models.Model):
    assessment_item = models.OneToOneField(
        AssessmentItem,
        on_delete=models.CASCADE,
        db_column='assessment_item_id',
        related_name='competence_links',
        primary_key=True,
        verbose_name='Оценочное задание',
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
        verbose_name = 'Связь задания и компетенции'
        verbose_name_plural = 'Связи заданий и компетенций'
        unique_together = (('assessment_item', 'competence'),)

    def __str__(self):
        return f'{self.assessment_item_id} -> {self.competence_id}'


class AssessmentOption(models.Model):
    id = models.AutoField(primary_key=True)
    assessment_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.CASCADE,
        db_column='assessment_item_id',
        related_name='options',
        verbose_name='Оценочное задание',
    )
    text = models.TextField(verbose_name='Текст варианта')
    is_correct = models.BooleanField(verbose_name='Верный вариант')
    sort_order = models.IntegerField(verbose_name='Порядок')

    class Meta:
        managed = False
        db_table = 'assessment_option'
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'

    def __str__(self):
        return f'{self.assessment_item_id}: {self.text[:50]}'


class AssessmentMatchLeftItem(models.Model):
    id = models.AutoField(primary_key=True)
    assessment_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.CASCADE,
        db_column='assessment_item_id',
        related_name='matching_left_items',
        verbose_name='Оценочное задание',
    )
    label = models.TextField(verbose_name='Метка')
    text = models.TextField(verbose_name='Текст')
    sort_order = models.IntegerField(verbose_name='Порядок')

    class Meta:
        managed = False
        db_table = 'assessment_match_left_item'
        verbose_name = 'Левая часть соответствия'
        verbose_name_plural = 'Левые части соответствия'

    def __str__(self):
        return f'{self.label}: {self.text[:40]}'


class AssessmentMatchRightItem(models.Model):
    id = models.AutoField(primary_key=True)
    assessment_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.CASCADE,
        db_column='assessment_item_id',
        related_name='matching_right_items',
        verbose_name='Оценочное задание',
    )
    label = models.TextField(verbose_name='Метка')
    text = models.TextField(verbose_name='Текст')
    sort_order = models.IntegerField(verbose_name='Порядок')

    class Meta:
        managed = False
        db_table = 'assessment_match_right_item'
        verbose_name = 'Правая часть соответствия'
        verbose_name_plural = 'Правые части соответствия'

    def __str__(self):
        return f'{self.label}: {self.text[:40]}'


class AssessmentMatchAnswer(models.Model):
    left_item = models.OneToOneField(
        AssessmentMatchLeftItem,
        on_delete=models.CASCADE,
        db_column='left_item_id',
        related_name='matched_answer',
        primary_key=True,
        verbose_name='Левый элемент',
    )
    right_item = models.ForeignKey(
        AssessmentMatchRightItem,
        on_delete=models.CASCADE,
        db_column='right_item_id',
        related_name='matching_answers',
        verbose_name='Правый элемент',
    )

    class Meta:
        managed = False
        db_table = 'assessment_match_answer'
        verbose_name = 'Ответ на соответствие'
        verbose_name_plural = 'Ответы на соответствие'
        unique_together = (('left_item', 'right_item'),)

    def __str__(self):
        return f'{self.left_item_id} -> {self.right_item_id}'


class AssessmentSequenceItem(models.Model):
    id = models.AutoField(primary_key=True)
    assessment_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.CASCADE,
        db_column='assessment_item_id',
        related_name='sequence_items',
        verbose_name='Оценочное задание',
    )
    text = models.TextField(verbose_name='Элемент последовательности')
    correct_order = models.IntegerField(verbose_name='Верный порядок')

    class Meta:
        managed = False
        db_table = 'assessment_sequence_item'
        verbose_name = 'Элемент последовательности'
        verbose_name_plural = 'Элементы последовательности'

    def __str__(self):
        return f'{self.correct_order}. {self.text[:50]}'


class AssessmentOpenAnswer(models.Model):
    id = models.AutoField(primary_key=True)
    assessment_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.CASCADE,
        db_column='assessment_item_id',
        related_name='open_answers',
        verbose_name='Оценочное задание',
    )
    text = models.TextField(verbose_name='Текст ответа')

    class Meta:
        managed = False
        db_table = 'assessment_open_answer'
        verbose_name = 'Открытый ответ'
        verbose_name_plural = 'Открытые ответы'

    def __str__(self):
        return self.text[:70]
