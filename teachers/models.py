from django.db import models


class Department(models.Model):
    id = models.AutoField(primary_key=True)
    number = models.CharField(max_length=20, unique=True, verbose_name='Номер кафедры')
    short_name = models.TextField(verbose_name='Краткое название')
    full_name = models.TextField(verbose_name='Полное название')
    head_teacher = models.ForeignKey(
        'Teacher',
        on_delete=models.PROTECT,
        db_column='head_teacher_id',
        related_name='headed_departments',
        null=True,
        blank=True,
        verbose_name='Заведующий кафедрой',
    )

    class Meta:
        managed = False
        db_table = 'department'
        verbose_name = 'Кафедра'
        verbose_name_plural = 'Кафедры'

    def __str__(self):
        return f'Кафедра {self.number} — {self.short_name}'


class Teacher(models.Model):
    id = models.AutoField(primary_key=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        db_column='department_id',
        related_name='teachers',
        verbose_name='Кафедра',
    )
    full_name = models.TextField(verbose_name='ФИО')
    academic_degree = models.ForeignKey(
        'core.AcademicDegree',
        on_delete=models.PROTECT,
        db_column='academic_degree_id',
        related_name='teachers',
        null=True,
        blank=True,
        verbose_name='Учёная степень',
    )
    academic_title = models.ForeignKey(
        'core.AcademicTitle',
        on_delete=models.PROTECT,
        db_column='academic_title_id',
        related_name='teachers',
        null=True,
        blank=True,
        verbose_name='Учёное звание',
    )

    class Meta:
        managed = False
        db_table = 'teacher'
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'

    def __str__(self):
        return self.full_name