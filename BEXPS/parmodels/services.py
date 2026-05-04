CURRENT_ORGANIZATION_SESSION_KEY = "current_organization_id"

from .models import OrganizationMembership


def get_current_membership(user, request=None):
    if not user.is_authenticated:
        return None

    memberships = (
        OrganizationMembership.objects
        .filter(user=user, status=OrganizationMembership.Status.ACTIVE)
        .select_related("organization", "department")
        .order_by("id")
    )

    if request is not None:
        organization_id = request.session.get(CURRENT_ORGANIZATION_SESSION_KEY)
        if organization_id:
            membership = memberships.filter(organization_id=organization_id).first()
            if membership:
                return membership
            request.session.pop(CURRENT_ORGANIZATION_SESSION_KEY, None)

    return memberships.first()


def get_current_organization(user, request=None):
    membership = get_current_membership(user, request=request)
    if membership:
        return membership.organization
    return None


def user_is_org_admin(user, request=None):
    membership = get_current_membership(user, request=request)
    return bool(
        membership
        and membership.role == OrganizationMembership.Role.ADMIN
    )
