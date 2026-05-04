from .services import get_current_membership


def current_organization(request):
    membership = None
    if request.user.is_authenticated:
        membership = get_current_membership(request.user, request=request)

    return {
        "current_membership": membership,
        "current_organization": membership.organization if membership else None,
    }
