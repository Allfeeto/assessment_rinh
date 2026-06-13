TEACHER_GROUP_NAME = 'Преподаватель'
SENIOR_TEACHER_GROUP_NAME = 'Старший преподаватель'

DOMAIN_MANAGER_REQUIRED_PERMISSIONS = (
    'programs.add_educationalprogram',
    'teachers.change_teacherprogramdiscipline',
    'assessment.add_assessmentitem',
)


def _is_authenticated(user):
    return bool(
        user
        and getattr(user, 'is_authenticated', False)
        and getattr(user, 'is_active', True)
    )


def is_platform_admin(user):
    return bool(_is_authenticated(user) and getattr(user, 'is_superuser', False))


def is_superuser_or_platform_admin(user):
    """Unrestricted application access.

    Senior teachers are domain managers, but their mutating actions are limited
    by managed departments. This helper excludes the senior teacher group from
    the legacy permission-based platform-admin shortcut because that group
    intentionally receives broad model permissions for the app UI.
    """
    if not _is_authenticated(user):
        return False
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True
    if _is_in_group(user, SENIOR_TEACHER_GROUP_NAME):
        return False
    try:
        return user.has_perms(DOMAIN_MANAGER_REQUIRED_PERMISSIONS)
    except AttributeError:
        return False


def _is_in_group(user, group_name):
    groups = getattr(user, 'groups', None)
    if groups is None:
        return False
    try:
        return groups.filter(name=group_name).exists()
    except AttributeError:
        return False


def is_domain_manager(user):
    """Can enter application management areas without relying on admin access."""
    if not _is_authenticated(user):
        return False
    if is_superuser_or_platform_admin(user):
        return True
    if _is_in_group(user, SENIOR_TEACHER_GROUP_NAME):
        return True
    return False


def is_staff_or_superuser(user):
    """Backward-compatible name for application managers."""
    return is_domain_manager(user)


def is_senior_teacher(user):
    return bool(_is_authenticated(user) and _is_in_group(user, SENIOR_TEACHER_GROUP_NAME))


def has_teacher_profile(user):
    return bool(_is_authenticated(user) and getattr(user, 'teacher_profile', None) is not None)


def can_use_teacher_workspace(user):
    return is_domain_manager(user) or has_teacher_profile(user)


def model_permission_codename(model, action):
    opts = model._meta
    return f'{opts.app_label}.{action}_{opts.model_name}'


def can_use_model_permission(user, model, action):
    if is_domain_manager(user):
        return True
    if not _is_authenticated(user):
        return False
    return user.has_perm(model_permission_codename(model, action))


def can_manage_teacher_assignments(user):
    if is_superuser_or_platform_admin(user):
        return True
    if is_senior_teacher(user):
        return get_user_departments(user).exists()
    if not _is_authenticated(user):
        return False
    return user.has_perms(
        (
            'teachers.add_teacherprogramdiscipline',
            'teachers.change_teacherprogramdiscipline',
            'teachers.delete_teacherprogramdiscipline',
        )
    )


def _teacher_department_ids(teacher):
    if teacher is None:
        return set()

    department_ids = set()
    department_id = getattr(teacher, 'department_id', None)
    if department_id:
        department_ids.add(department_id)

    departments = getattr(teacher, 'departments', None)
    if departments is not None:
        try:
            department_ids.update(departments.values_list('id', flat=True))
        except (AttributeError, ValueError):
            pass

    return department_ids


def get_user_departments(user):
    """Departments the user may manage.

    Superusers/platform admins manage all departments. A senior teacher manages
    the departments attached to their Teacher profile, including the legacy
    primary department field.
    """
    from teachers.models import Department

    if not _is_authenticated(user):
        return Department.objects.none()
    if is_superuser_or_platform_admin(user):
        return Department.objects.all()
    if not is_senior_teacher(user):
        return Department.objects.none()

    teacher = getattr(user, 'teacher_profile', None)
    department_ids = _teacher_department_ids(teacher)
    if not department_ids:
        return Department.objects.none()
    return Department.objects.filter(pk__in=department_ids)


def get_user_department_ids(user):
    if not _is_authenticated(user):
        return set()
    if is_superuser_or_platform_admin(user):
        return None
    return set(get_user_departments(user).values_list('id', flat=True))


def can_manage_department(user, department):
    if is_superuser_or_platform_admin(user):
        return True
    department_id = getattr(department, 'id', department)
    if not department_id or not is_senior_teacher(user):
        return False
    return department_id in set(get_user_departments(user).values_list('id', flat=True))


def can_manage_department_scoped_records(user):
    if is_superuser_or_platform_admin(user):
        return True
    return bool(is_senior_teacher(user) and get_user_departments(user).exists())


def can_manage_competence(user, competence):
    if is_superuser_or_platform_admin(user):
        return True
    if competence is None or not is_senior_teacher(user):
        return False
    educational_program = getattr(competence, 'educational_program', None)
    department_id = getattr(educational_program, 'department_id', None)
    if department_id is None:
        department_id = getattr(competence, 'educational_program__department_id', None)
    return can_manage_department(user, department_id)


def filter_competences_for_management(user, queryset):
    if is_superuser_or_platform_admin(user):
        return queryset
    if not is_senior_teacher(user):
        return queryset.none()

    department_ids = set(get_user_departments(user).values_list('id', flat=True))
    if not department_ids:
        return queryset.none()
    return queryset.filter(educational_program__department_id__in=department_ids)


def can_manage_teacher(user, teacher):
    if is_superuser_or_platform_admin(user):
        return True
    if teacher is None or not is_senior_teacher(user):
        return False
    user_department_ids = set(get_user_departments(user).values_list('id', flat=True))
    if not user_department_ids:
        return False
    return bool(_teacher_department_ids(teacher) & user_department_ids)


def can_manage_program_discipline(user, program_discipline):
    if is_superuser_or_platform_admin(user):
        return True
    if program_discipline is None or not is_senior_teacher(user):
        return False
    department_id = getattr(program_discipline, 'department_id', None)
    if not department_id:
        return False
    return department_id in set(get_user_departments(user).values_list('id', flat=True))


def assignment_denial_reason(user, teacher, program_discipline):
    if is_superuser_or_platform_admin(user):
        return ''
    if not _is_authenticated(user) or not is_senior_teacher(user):
        return 'Назначения может менять только старший преподаватель или администратор.'

    user_department_ids = set(get_user_departments(user).values_list('id', flat=True))
    if not user_department_ids:
        return 'Для вашей учётной записи не указаны кафедры управления.'

    if teacher is None:
        return 'Преподаватель не найден.'

    program_discipline_department_id = getattr(program_discipline, 'department_id', None)
    if not program_discipline_department_id:
        return 'Нельзя назначить преподавателя: у дисциплины не указана кафедра.'
    if program_discipline_department_id not in user_department_ids:
        return 'Нельзя назначить преподавателя: дисциплина относится к другой кафедре.'

    teacher_department_ids = _teacher_department_ids(teacher)
    if program_discipline_department_id not in teacher_department_ids:
        return 'Нельзя назначить преподавателя: преподаватель не относится к кафедре этой дисциплины.'

    return ''


def can_assign_teacher_to_program_discipline(user, teacher, program_discipline):
    return assignment_denial_reason(user, teacher, program_discipline) == ''


def filter_teachers_for_assignment(user, queryset):
    if is_superuser_or_platform_admin(user):
        return queryset
    if not is_senior_teacher(user):
        return queryset.none()

    department_ids = set(get_user_departments(user).values_list('id', flat=True))
    if not department_ids:
        return queryset.none()

    return queryset.filter(
        models_q_for_teacher_departments(department_ids)
    ).distinct()


def filter_program_disciplines_for_assignment(user, queryset):
    if is_superuser_or_platform_admin(user):
        return queryset
    if not is_senior_teacher(user):
        return queryset.none()

    department_ids = set(get_user_departments(user).values_list('id', flat=True))
    if not department_ids:
        return queryset.none()
    return queryset.filter(department_id__in=department_ids)


def models_q_for_teacher_departments(department_ids):
    from django.db.models import Q

    return Q(department_id__in=department_ids) | Q(departments__id__in=department_ids)


def get_assignment_availability(user, teacher, program_disciplines):
    availability = {}
    for program_discipline in program_disciplines:
        reason = assignment_denial_reason(user, teacher, program_discipline)
        availability[program_discipline.id] = {
            'can_assign': reason == '',
            'cannot_assign_reason': reason,
        }
    return availability
