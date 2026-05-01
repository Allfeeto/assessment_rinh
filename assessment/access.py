from disciplines.models import ProgramDiscipline
from teachers.models import TeacherProgramDiscipline


def allowed_program_discipline_ids_for_user(user, *, include_deleted=False, deleted_only=False):
    if not user.is_authenticated:
        return []

    queryset = ProgramDiscipline.objects.all()
    if deleted_only:
        queryset = queryset.filter(educational_program__is_deleted=True)
    elif not include_deleted:
        queryset = queryset.filter(educational_program__is_deleted=False)

    if user.is_superuser:
        return list(queryset.values_list('id', flat=True))

    teacher = getattr(user, 'teacher_profile', None)
    if not teacher:
        return []

    return list(
        TeacherProgramDiscipline.objects.filter(
            teacher=teacher,
            program_discipline_id__in=queryset.values_list('id', flat=True),
        ).values_list(
            'program_discipline_id',
            flat=True,
        )
    )


def can_access_program_discipline(user, program_discipline_id, *, allow_staff=False):
    if not user.is_authenticated:
        return False

    if user.is_superuser or (allow_staff and user.is_staff):
        return True

    return int(program_discipline_id) in set(allowed_program_discipline_ids_for_user(user))
