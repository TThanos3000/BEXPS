from rest_framework.permissions import BasePermission

from .permissions import has_permission
from .services import get_current_organization


class OrganizationRolePermission(BasePermission):
    message = "Недостаточно прав для выполнения действия."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        required_permission = view.get_required_permission() if hasattr(view, "get_required_permission") else None
        if required_permission and not has_permission(request.user, required_permission, request=request):
            return False

        return get_current_organization(request.user, request=request) is not None

    def has_object_permission(self, request, view, obj):
        organization = get_current_organization(request.user, request=request)
        if organization is None:
            return False

        object_organization_id = getattr(obj, "organization_id", None)
        if object_organization_id is None and hasattr(obj, "organization"):
            object_organization_id = getattr(obj.organization, "id", None)

        if object_organization_id is not None and object_organization_id != organization.id:
            return False

        required_permission = view.get_required_permission() if hasattr(view, "get_required_permission") else None
        if required_permission and not has_permission(request.user, required_permission, request=request):
            return False

        return True

