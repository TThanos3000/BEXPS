from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Application,
    ApplicationStatus,
    Department,
    Equipment,
    EquipmentStatus,
    EquipmentType,
    History_Application,
    History_Equipment,
    Location,
    OrganizationMembership,
)


class CurrentOrganizationSerializerMixin:
    def get_current_organization(self):
        return self.context.get("organization")

    def validate_location_in_organization(self, location):
        organization = self.get_current_organization()
        if location and organization and location.organization_id != organization.id:
            raise serializers.ValidationError("Локация должна принадлежать текущей организации.")
        return location

    def validate_equipment_in_organization(self, equipment):
        organization = self.get_current_organization()
        if equipment and organization and equipment.organization_id != organization.id:
            raise serializers.ValidationError("Оборудование должно принадлежать текущей организации.")
        return equipment

    def validate_user_in_organization(self, user):
        organization = self.get_current_organization()
        if not user or not organization:
            return user
        exists = OrganizationMembership.objects.filter(
            organization=organization,
            user=user,
            status=OrganizationMembership.Status.ACTIVE,
        ).exists()
        if not exists:
            raise serializers.ValidationError("Пользователь должен состоять в текущей организации.")
        return user

    def validate_department_in_organization(self, department):
        organization = self.get_current_organization()
        if department and organization and department.organization_id != organization.id:
            raise serializers.ValidationError("Департамент должен принадлежать текущей организации.")
        return department


class LocationSerializer(CurrentOrganizationSerializerMixin, serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    location_type_display = serializers.CharField(source="get_location_type_display", read_only=True)

    class Meta:
        model = Location
        fields = [
            "id",
            "organization",
            "organization_name",
            "parent",
            "parent_name",
            "name",
            "location_type",
            "location_type_display",
            "description",
            "address_location",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]

    def validate_parent(self, parent):
        return self.validate_location_in_organization(parent)


class EquipmentSerializer(CurrentOrganizationSerializerMixin, serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)
    type_name = serializers.CharField(source="type_equipment.name", read_only=True)

    class Meta:
        model = Equipment
        fields = [
            "id",
            "organization",
            "organization_name",
            "location",
            "location_name",
            "name_equipment",
            "about",
            "inventory_number",
            "external_id",
            "date_input",
            "status",
            "status_name",
            "type_equipment",
            "type_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]

    def validate_location(self, location):
        return self.validate_location_in_organization(location)


class ApplicationSerializer(CurrentOrganizationSerializerMixin, serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    equipment_name = serializers.CharField(source="equipment.name_equipment", read_only=True)
    creator_name = serializers.SerializerMethodField()
    executor_name = serializers.SerializerMethodField()
    status_name = serializers.CharField(source="status.name", read_only=True)
    priority_name = serializers.CharField(source="priority.name", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "organization",
            "organization_name",
            "location",
            "location_name",
            "equipment",
            "equipment_name",
            "name_application",
            "date_create",
            "about",
            "deadline",
            "creator",
            "creator_name",
            "executor",
            "executor_name",
            "priority",
            "priority_name",
            "status",
            "status_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "creator", "created_at", "updated_at"]

    def get_creator_name(self, obj):
        return obj.creator.get_full_name() or obj.creator.email or obj.creator.username if obj.creator else ""

    def get_executor_name(self, obj):
        return obj.executor.get_full_name() or obj.executor.email or obj.executor.username if obj.executor else ""

    def validate_location(self, location):
        return self.validate_location_in_organization(location)

    def validate_equipment(self, equipment):
        return self.validate_equipment_in_organization(equipment)

    def validate_executor(self, executor):
        return self.validate_user_in_organization(executor)


class ApplicationStatusChangeSerializer(CurrentOrganizationSerializerMixin, serializers.Serializer):
    status = serializers.PrimaryKeyRelatedField(queryset=ApplicationStatus.objects.filter(is_active=True))
    comment = serializers.CharField(required=False, allow_blank=True)


class EquipmentStatusChangeSerializer(CurrentOrganizationSerializerMixin, serializers.Serializer):
    status = serializers.PrimaryKeyRelatedField(queryset=EquipmentStatus.objects.filter(is_active=True))
    application = serializers.PrimaryKeyRelatedField(
        queryset=Application.objects.all(),
        required=False,
        allow_null=True,
    )
    maintenance_type = serializers.CharField(required=False, allow_blank=True, default="Изменение статуса")
    description = serializers.CharField(required=False, allow_blank=True)
    result = serializers.CharField(required=False, allow_blank=True)

    def validate_application(self, application):
        organization = self.get_current_organization()
        if application and organization and application.organization_id != organization.id:
            raise serializers.ValidationError("Заявка должна принадлежать текущей организации.")
        return application


class OrganizationUserSerializer(CurrentOrganizationSerializerMixin, serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True)
    email = serializers.EmailField(source="user.email", required=False, allow_blank=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = [
            "id",
            "user_id",
            "username",
            "first_name",
            "last_name",
            "email",
            "organization",
            "organization_name",
            "role",
            "role_display",
            "department",
            "department_name",
            "position",
            "date_reception",
            "joined_at",
        ]
        read_only_fields = ["id", "user_id", "username", "organization", "organization_name", "joined_at"]

    def validate_department(self, department):
        return self.validate_department_in_organization(department)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        for field, value in user_data.items():
            setattr(user, field, value)
        if user_data:
            user.save(update_fields=list(user_data.keys()))
        return super().update(instance, validated_data)


User = get_user_model()

