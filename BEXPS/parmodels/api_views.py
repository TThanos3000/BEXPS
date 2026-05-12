from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .api_permissions import OrganizationRolePermission
from .models import (
    Application,
    Equipment,
    History_Application,
    History_Equipment,
    Location,
    OrganizationMembership,
)
from .permissions import can_update_application_status, has_permission
from .serializers import (
    ApplicationSerializer,
    ApplicationStatusChangeSerializer,
    EquipmentSerializer,
    EquipmentStatusChangeSerializer,
    LocationSerializer,
    OrganizationUserSerializer,
)
from .services import get_current_organization


class OrganizationScopedViewSetMixin:
    permission_classes = [IsAuthenticated, OrganizationRolePermission]
    action_permissions = {}

    def get_current_organization(self):
        return get_current_organization(self.request.user, request=self.request)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization"] = self.get_current_organization()
        return context

    def get_required_permission(self):
        return self.action_permissions.get(self.action)


class LocationViewSet(OrganizationScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = LocationSerializer
    action_permissions = {
        "list": "locations.view",
        "retrieve": "locations.view",
        "create": "locations.create",
        "update": "locations.update",
        "partial_update": "locations.update",
        "destroy": "locations.delete",
    }

    def get_queryset(self):
        organization = self.get_current_organization()
        if organization is None:
            return Location.objects.none()
        return (
            Location.objects
            .filter(organization=organization)
            .select_related("organization", "parent")
            .order_by("parent_id", "location_type", "name")
        )

    @swagger_auto_schema(tags=["Locations"], operation_description="Список локаций текущей организации.")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Locations"], operation_description="Создание локации в текущей организации.")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Locations"], operation_description="Детальная информация по локации.")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Locations"], operation_description="Полное обновление локации.")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Locations"], operation_description="Частичное обновление локации.")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Locations"], operation_description="Удаление локации.")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(organization=self.get_current_organization())


class ApplicationViewSet(OrganizationScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    action_permissions = {
        "list": "applications.view",
        "retrieve": "applications.view",
        "create": "applications.create",
        "update": "applications.update",
        "partial_update": "applications.update",
        "destroy": "applications.delete",
        "change_status": "applications.update_status",
    }

    def get_queryset(self):
        organization = self.get_current_organization()
        if organization is None:
            return Application.objects.none()
        return (
            Application.objects
            .filter(organization=organization)
            .select_related("organization", "location", "equipment", "creator", "executor", "priority", "status")
            .order_by("-created_at")
        )

    @swagger_auto_schema(tags=["Applications"], operation_description="Список заявок текущей организации.")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Applications"], operation_description="Создание заявки в текущей организации.")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Applications"], operation_description="Детальная информация по заявке.")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Applications"], operation_description="Полное обновление заявки.")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Applications"], operation_description="Частичное обновление заявки.")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Applications"], operation_description="Удаление заявки.")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        organization = self.get_current_organization()
        application = serializer.save(organization=organization, creator=self.request.user)
        if application.date_create is None:
            application.date_create = timezone.now()
            application.save(update_fields=["date_create"])
        History_Application.objects.create(
            organization=organization,
            application=application,
            user=self.request.user,
            status_old=application.status,
            status_new=application.status,
            comment="Заявка создана",
        )

    def perform_update(self, serializer):
        application = self.get_object()
        old_status = application.status
        application = serializer.save()
        if getattr(old_status, "id", None) != application.status_id:
            History_Application.objects.create(
                organization=application.organization,
                application=application,
                user=self.request.user,
                status_old=old_status,
                status_new=application.status,
                comment="Статус изменен через API",
            )

    @swagger_auto_schema(
        method="post",
        request_body=ApplicationStatusChangeSerializer,
        responses={200: ApplicationSerializer},
        tags=["Applications"],
        operation_description="Изменение статуса заявки с записью истории.",
    )
    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        application = self.get_object()
        if not can_update_application_status(request.user, application, request=request):
            raise PermissionDenied("Недостаточно прав для изменения статуса заявки.")

        serializer = ApplicationStatusChangeSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        old_status = application.status
        new_status = serializer.validated_data["status"]
        if old_status and old_status.id == new_status.id:
            return Response(self.get_serializer(application).data)

        application.status = new_status
        application.save(update_fields=["status", "updated_at"])
        History_Application.objects.create(
            organization=application.organization,
            application=application,
            user=request.user,
            status_old=old_status,
            status_new=new_status,
            comment=serializer.validated_data.get("comment", ""),
        )
        return Response(self.get_serializer(application).data)


class EquipmentViewSet(OrganizationScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EquipmentSerializer
    action_permissions = {
        "list": "equipment.view",
        "retrieve": "equipment.view",
        "create": "equipment.create",
        "update": "equipment.update",
        "partial_update": "equipment.update",
        "destroy": "equipment.delete",
        "change_status": "equipment.update_status",
    }

    def get_queryset(self):
        organization = self.get_current_organization()
        if organization is None:
            return Equipment.objects.none()
        return (
            Equipment.objects
            .filter(organization=organization)
            .select_related("organization", "location", "status", "type_equipment")
            .order_by("name_equipment", "inventory_number")
        )

    @swagger_auto_schema(tags=["Equipment"], operation_description="Список оборудования текущей организации.")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Equipment"], operation_description="Создание оборудования в текущей организации.")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Equipment"], operation_description="Детальная информация по оборудованию.")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Equipment"], operation_description="Полное обновление оборудования.")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Equipment"], operation_description="Частичное обновление оборудования.")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Equipment"], operation_description="Удаление оборудования.")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(organization=self.get_current_organization())

    def perform_update(self, serializer):
        equipment = self.get_object()
        old_status = equipment.status
        equipment = serializer.save()
        if getattr(old_status, "id", None) != equipment.status_id:
            self._create_status_history(equipment, old_status, equipment.status, "Статус изменен через API")

    def _create_status_history(self, equipment, old_status, new_status, description, application=None):
        old_name = old_status.name if old_status else "Без статуса"
        new_name = new_status.name if new_status else "Без статуса"
        History_Equipment.objects.create(
            organization=equipment.organization,
            equipment=equipment,
            application=application,
            user=self.request.user,
            maintenance_type="Изменение статуса",
            description=description,
            result=f"{old_name} → {new_name}",
            performed_at=timezone.now(),
        )

    @swagger_auto_schema(
        method="post",
        request_body=EquipmentStatusChangeSerializer,
        responses={200: EquipmentSerializer},
        tags=["Equipment"],
        operation_description="Изменение статуса оборудования с записью истории.",
    )
    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        equipment = self.get_object()
        serializer = EquipmentStatusChangeSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        old_status = equipment.status
        new_status = serializer.validated_data["status"]
        if old_status and old_status.id == new_status.id:
            return Response(self.get_serializer(equipment).data)

        equipment.status = new_status
        equipment.save(update_fields=["status", "updated_at"])
        self._create_status_history(
            equipment,
            old_status,
            new_status,
            serializer.validated_data.get("description", ""),
            serializer.validated_data.get("application"),
        )
        return Response(self.get_serializer(equipment).data)


class OrganizationUserViewSet(OrganizationScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = OrganizationUserSerializer
    lookup_field = "user_id"
    action_permissions = {
        "list": "users.view",
        "retrieve": "users.view",
    }

    def get_queryset(self):
        organization = self.get_current_organization()
        if organization is None:
            return OrganizationMembership.objects.none()
        return (
            OrganizationMembership.objects
            .filter(organization=organization, status=OrganizationMembership.Status.ACTIVE)
            .select_related("user", "organization", "department")
            .order_by("user__last_name", "user__first_name", "user__email")
        )

    @swagger_auto_schema(tags=["Users"], operation_description="Пользователи текущей организации.")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Users"], operation_description="Данные пользователя в текущей организации.")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["Users"], operation_description="Частичное обновление пользователя или членства.")
    def partial_update(self, request, *args, **kwargs):
        membership = self.get_object()
        if membership.user_id == request.user.id:
            if not has_permission(request.user, "profile.update", request=request):
                raise PermissionDenied("Недостаточно прав для редактирования профиля.")
        elif not has_permission(request.user, "users.update", request=request):
            raise PermissionDenied("Редактировать чужих пользователей может только администратор.")

        serializer = self.get_serializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_required_permission(self):
        if self.action == "partial_update":
            return None
        return super().get_required_permission()


User = get_user_model()
