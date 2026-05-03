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


def _is_in_group(user, group_name):
    groups = getattr(user, 'groups', None)
    if groups is None:
        return False
    try:
        return groups.filter(name=group_name).exists()
    except AttributeError:
        return False


def is_domain_manager(user):
    """Full application access without relying on Django admin access."""
    if not _is_authenticated(user):
        return False
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True
    if _is_in_group(user, SENIOR_TEACHER_GROUP_NAME):
        return True
    try:
        return user.has_perms(DOMAIN_MANAGER_REQUIRED_PERMISSIONS)
    except AttributeError:
        return False


def is_staff_or_superuser(user):
    """Backward-compatible name for full application managers."""
    return is_domain_manager(user)


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
    if is_domain_manager(user):
        return True
    if not _is_authenticated(user):
        return False
    return user.has_perms(
        (
            'teachers.add_teacherprogramdiscipline',
            'teachers.change_teacherprogramdiscipline',
            'teachers.delete_teacherprogramdiscipline',
        )
    )
