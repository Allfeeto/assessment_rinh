from django.db import models


class EducationLevel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, verbose_name='Наименование')

    class Meta:
        managed = False
        db_table = 'education_level'
        verbose_name = 'Уровень образования'
        verbose_name_plural = 'Уровни образования'

    def __str__(self):
        return self.name


class Department(models.Model):
    id = models.AutoField(primary_key=True)
    short_name = models.TextField(verbose_name='Краткое наименование')
    full_name = models.TextField(verbose_name='Полное наименование')

    class Meta:
        managed = False
        db_table = 'department'
        verbose_name = 'Кафедра'
        verbose_name_plural = 'Кафедры'

    def __str__(self):
        return self.short_name


class EducationalProgram(models.Model):
    id = models.AutoField(primary_key=True)
    education_level = models.ForeignKey(
        EducationLevel,
        on_delete=models.PROTECT,
        db_column='education_level_id',
        related_name='educational_programs',
        verbose_name='Уровень образования',
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        db_column='department_id',
        related_name='educational_programs',
        verbose_name='Кафедра',
    )
    code = models.TextField(unique=True, verbose_name='Код программы')
    name = models.TextField(verbose_name='Наименование программы')

    class Meta:
        managed = False
        db_table = 'educational_program'
        verbose_name = 'Образовательная программа'
        verbose_name_plural = 'Образовательные программы'

    def __str__(self):
        return f'{self.code} {self.name}'