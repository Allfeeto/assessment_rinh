def is_staff_or_superuser(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or user.is_superuser)
    )


def model_permission_codename(model, action):
    opts = model._meta
    return f'{opts.app_label}.{action}_{opts.model_name}'


def can_use_model_permission(user, model, action):
    if is_staff_or_superuser(user):
        return True
    if not user or not user.is_authenticated:
        return False
    return user.has_perm(model_permission_codename(model, action))


def can_manage_teacher_assignments(user):
    if is_staff_or_superuser(user):
        return True
    if not user or not user.is_authenticated:
        return False
    return user.has_perms(
        (
            'teachers.add_teacherprogramdiscipline',
            'teachers.change_teacherprogramdiscipline',
            'teachers.delete_teacherprogramdiscipline',
        )
    )
