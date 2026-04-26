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


class CompetenceType(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, verbose_name='Наименование')

    class Meta:
        managed = False
        db_table = 'competence_type'
        verbose_name = 'Тип компетенции'
        verbose_name_plural = 'Типы компетенций'

    def __str__(self):
        return self.name


class AssessmentItemType(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True, verbose_name='Код')
    name = models.TextField(unique=True, verbose_name='Наименование')

    class Meta:
        managed = False
        db_table = 'assessment_item_type'
        verbose_name = 'Тип задания'
        verbose_name_plural = 'Типы заданий'

    def __str__(self):
        return self.name


class AcademicDegree(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, verbose_name='Наименование')

    class Meta:
        managed = False
        db_table = 'academic_degree'
        verbose_name = 'Учёная степень'
        verbose_name_plural = 'Учёные степени'

    def __str__(self):
        return self.name


class AcademicTitle(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(unique=True, verbose_name='Наименование')

    class Meta:
        managed = False
        db_table = 'academic_title'
        verbose_name = 'Учёное звание'
        verbose_name_plural = 'Учёные звания'

    def __str__(self):
        return self.name
