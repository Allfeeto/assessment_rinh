from django.core.exceptions import ValidationError
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

    def clean(self):
        super().clean()
        if not self.head_teacher_id:
            return

        teacher = (
            Teacher.objects.filter(pk=self.head_teacher_id)
            .prefetch_related('departments')
            .first()
        )
        if teacher is None or not self.pk:
            return

        teacher_department_ids = {teacher.department_id}
        teacher_department_ids.update(teacher.departments.values_list('id', flat=True))
        if self.pk not in teacher_department_ids:
            raise ValidationError({
                'head_teacher': 'Заведующий кафедрой должен быть преподавателем этой же кафедры.'
            })


class Teacher(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.SET_NULL,
        db_column='user_id',
        related_name='teacher_profile',
        null=True,
        blank=True,
        verbose_name='Пользователь сайта',
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        db_column='department_id',
        related_name='teachers',
        verbose_name='Основная кафедра',
    )
    departments = models.ManyToManyField(
        Department,
        db_table='teacher_departments',
        related_name='teachers_by_membership',
        blank=True,
        verbose_name='Кафедры преподавателя',
        help_text='Дополнительные кафедры преподавателя; основная кафедра хранится в legacy-поле выше.',
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

    @property
    def departments_display(self):
        try:
            departments = list(self.departments.all())
        except ValueError:
            departments = []
        if departments:
            return ', '.join(
                department.short_name
                for department in sorted(departments, key=lambda item: item.number)
            )
        department = getattr(self, 'department', None)
        return department.short_name if department else ''

    def ensure_primary_department_membership(self):
        if self.pk and self.department_id:
            self.departments.add(self.department_id)


class TeacherProgramDiscipline(models.Model):
    id = models.AutoField(primary_key=True)
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        db_column='teacher_id',
        related_name='teacher_program_disciplines',
        verbose_name='Преподаватель',
    )
    program_discipline = models.ForeignKey(
        'disciplines.ProgramDiscipline',
        on_delete=models.CASCADE,
        db_column='program_discipline_id',
        related_name='teacher_program_disciplines',
        verbose_name='Дисциплина учебного плана',
    )

    class Meta:
        managed = False
        db_table = 'teacher_program_discipline'
        verbose_name = 'Привязка преподавателя к дисциплине учебного плана'
        verbose_name_plural = 'Привязки преподавателей к дисциплинам учебных планов'
        constraints = [
            models.UniqueConstraint(
                fields=('teacher', 'program_discipline'),
                name='teacher_program_discipline_teacher_id_program_discipline_id_key',
            )
        ]

    def __str__(self):
        return f'{self.teacher.full_name} -> {self.program_discipline}'
