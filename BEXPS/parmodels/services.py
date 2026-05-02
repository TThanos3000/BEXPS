from .models import OrganizationMembership


def get_current_membership(user):
    if not user.is_authenticated:
        return None
    return (
        OrganizationMembership.objects
        .filter(user=user, status=OrganizationMembership.Status.ACTIVE)
        .select_related("organization", "department")
        .order_by("id")
        .first()
    )


def get_current_organization(user):
    membership = get_current_membership(user)
    if membership:
        return membership.organization
    return None


def user_is_org_admin(user):
    membership = get_current_membership(user)
    return bool(
        membership
        and membership.role == OrganizationMembership.Role.ADMIN
    )
