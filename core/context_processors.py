from .permissions import can_use_teacher_workspace, is_domain_manager


def role_flags(request):
    user = getattr(request, 'user', None)
    return {
        'can_use_teacher_workspace': can_use_teacher_workspace(user),
        'is_domain_manager': is_domain_manager(user),
    }
