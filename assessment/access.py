from disciplines.models import ProgramDiscipline
from core.permissions import (
    filter_program_disciplines_for_assignment,
    is_senior_teacher,
    is_superuser_or_platform_admin,
)


def program_discipline_queryset_for_user(user, *, include_deleted=False, deleted_only=False):
    queryset = ProgramDiscipline.objects.all()
    if deleted_only:
        queryset = queryset.filter(educational_program__is_deleted=True)
    elif not include_deleted:
        queryset = queryset.filter(educational_program__is_deleted=False)

    if not user.is_authenticated:
        return queryset.none()

    if is_superuser_or_platform_admin(user):
        return queryset

    if is_senior_teacher(user):
        return filter_program_disciplines_for_assignment(user, queryset)

    teacher = getattr(user, 'teacher_profile', None)
    if not teacher:
        return queryset.none()

    return queryset.filter(
        teacher_program_disciplines__teacher=teacher,
    ).distinct()


def allowed_program_discipline_ids_for_user(user, *, include_deleted=False, deleted_only=False):
    if not user.is_authenticated:
        return []

    return list(
        program_discipline_queryset_for_user(
            user,
            include_deleted=include_deleted,
            deleted_only=deleted_only,
        ).values_list('id', flat=True)
    )


def can_access_program_discipline(user, program_discipline_id, *, allow_staff=False):
    if not user.is_authenticated:
        return False

    if is_superuser_or_platform_admin(user):
        return True

    return int(program_discipline_id) in set(allowed_program_discipline_ids_for_user(user))
