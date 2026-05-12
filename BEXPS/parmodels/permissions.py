from django.core.exceptions import PermissionDenied

from .models import OrganizationMembership
from .services import get_current_membership


ROLE_PERMISSIONS = {
    OrganizationMembership.Role.ADMIN: {
        "applications.view",
        "applications.create",
        "applications.update",
        "applications.delete",
        "applications.update_status",
        "locations.view",
        "locations.create",
        "locations.update",
        "locations.delete",
        "equipment.view",
        "equipment.create",
        "equipment.update",
        "equipment.delete",
        "equipment.update_status",
        "users.view",
        "users.invite",
        "users.create",
        "users.update",
        "users.delete",
        "profile.view",
        "profile.update",
        "invitations.view",
        "invitations.create",
    },
    OrganizationMembership.Role.DISPATCHER: {
        "applications.view",
        "applications.create",
        "applications.update",
        "applications.delete",
        "applications.update_status",
        "locations.view",
        "locations.create",
        "equipment.view",
        "equipment.update",
        "equipment.update_status",
        "users.view",
        "profile.view",
        "profile.update",
    },
    OrganizationMembership.Role.ENGINEER: {
        "applications.view",
        "applications.update",
        "applications.update_status",
        "locations.view",
        "equipment.view",
        "users.view",
        "profile.view",
        "profile.update",
    },
    OrganizationMembership.Role.CHIEF_ENGINEER: {
        "applications.view",
        "applications.update",
        "applications.update_status",
        "locations.view",
        "locations.create",
        "locations.update",
        "equipment.view",
        "users.view",
        "profile.view",
        "profile.update",
    },
}


def get_user_permissions(user, request=None):
    membership = get_current_membership(user, request=request)
    if membership is None:
        return set()
    return ROLE_PERMISSIONS.get(membership.role, set())


def has_permission(user, permission, request=None):
    return permission in get_user_permissions(user, request=request)


def require_permission(user, permission, request=None):
    if not has_permission(user, permission, request=request):
        raise PermissionDenied


def can_update_application_status(user, application, request=None):
    membership = get_current_membership(user, request=request)
    if membership is None:
        return False
    if "applications.update_status" not in ROLE_PERMISSIONS.get(membership.role, set()):
        return False
    if membership.role == OrganizationMembership.Role.ENGINEER:
        return application.executor_id == user.id
    return True


def require_application_status_permission(user, application, request=None):
    if not can_update_application_status(user, application, request=request):
        raise PermissionDenied


def permission_flags(user, request=None):
    permissions = get_user_permissions(user, request=request)
    return {
        "can_view_application": "applications.view" in permissions,
        "can_create_application": "applications.create" in permissions,
        "can_update_application": "applications.update" in permissions,
        "can_delete_application": "applications.delete" in permissions,
        "can_update_application_status": "applications.update_status" in permissions,
        "can_view_location": "locations.view" in permissions,
        "can_create_location": "locations.create" in permissions,
        "can_update_location": "locations.update" in permissions,
        "can_delete_location": "locations.delete" in permissions,
        "can_create_location_model": "locations.update" in permissions,
        "can_view_equipment": "equipment.view" in permissions,
        "can_create_equipment": "equipment.create" in permissions,
        "can_update_equipment": "equipment.update" in permissions,
        "can_delete_equipment": "equipment.delete" in permissions,
        "can_update_equipment_status": "equipment.update_status" in permissions,
        "can_view_users": "users.view" in permissions,
        "can_invite_users": "users.invite" in permissions,
    }
