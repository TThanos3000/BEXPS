from django.contrib import admin
from .models import (
    Application,
    ApplicationPriority,
    ApplicationStatus,
    Department,
    Equipment,
    EquipmentStatus,
    EquipmentType,
    File,
    History_Application,
    History_Equipment,
    Location,
    LocationModel,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location_type", "organization", "parent")
    list_filter = ("organization", "location_type")
    search_fields = ("name", "description", "address_location", "organization__name", "parent__name")
    autocomplete_fields = ("organization", "parent")
    ordering = ("organization__name", "parent_id", "id")


@admin.register(LocationModel)
class LocationModelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location", "created_at", "updated_at")
    list_filter = ("location__organization", "created_at", "updated_at")
    search_fields = ("name", "location__name", "location__organization__name")
    autocomplete_fields = ("location",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(EquipmentStatus)
class EquipmentStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "description")
    ordering = ("code",)


@admin.register(EquipmentType)
class EquipmentTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "description")
    ordering = ("code",)


@admin.register(ApplicationStatus)
class ApplicationStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "color_code", "is_active", "is_system")
    list_filter = ("is_active", "is_system")
    search_fields = ("code", "name", "description", "color_code")
    ordering = ("code",)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(ApplicationPriority)
class ApplicationPriorityAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "color_code", "weight", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "description", "color_code")
    ordering = ("weight", "code")


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name_equipment", "organization", "location", "status", "type_equipment", "inventory_number")
    list_filter = ("organization", "location", "status", "type_equipment", "date_input")
    search_fields = (
        "name_equipment",
        "about",
        "inventory_number",
        "external_id",
        "organization__name",
        "location__name",
    )
    autocomplete_fields = ("organization", "location", "status", "type_equipment")
    date_hierarchy = "created_at"
    ordering = ("name_equipment",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "name_application", "organization", "location", "equipment", "priority", "status", "executor")
    list_filter = ("organization", "location", "priority", "status", "deadline", "created_at")
    search_fields = (
        "name_application",
        "about",
        "organization__name",
        "location__name",
        "equipment__name_equipment",
        "creator__username",
        "creator__email",
        "executor__username",
        "executor__email",
    )
    autocomplete_fields = (
        "organization",
        "location",
        "equipment",
        "creator",
        "executor",
        "priority",
        "status",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("id", "file_name", "organization", "file_type", "file_size", "uploaded_by", "created_at")
    list_filter = ("organization", "file_type", "created_at")
    search_fields = ("file_name", "file_path", "file_type", "organization__name", "uploaded_by__username", "uploaded_by__email")
    autocomplete_fields = ("organization", "uploaded_by")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(History_Application)
class HistoryApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "application", "user", "status_old", "status_new", "file", "changed_at")
    list_filter = ("organization", "status_old", "status_new", "changed_at")
    search_fields = (
        "application__name_application",
        "comment",
        "organization__name",
        "user__username",
        "user__email",
        "file__file_name",
    )
    autocomplete_fields = ("organization", "application", "user", "status_old", "status_new", "file")
    date_hierarchy = "changed_at"
    ordering = ("-changed_at",)


@admin.register(History_Equipment)
class HistoryEquipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "equipment", "application", "user", "maintenance_type", "file", "performed_at")
    list_filter = ("organization", "maintenance_type", "performed_at")
    search_fields = (
        "equipment__name_equipment",
        "application__name_application",
        "maintenance_type",
        "description",
        "result",
        "organization__name",
        "user__username",
        "user__email",
        "file__file_name",
    )
    autocomplete_fields = ("organization", "equipment", "application", "user", "file")
    date_hierarchy = "performed_at"
    ordering = ("-performed_at", "-id")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "legal_name", "inn", "status", "created_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "legal_name", "inn")
    autocomplete_fields = ("created_by",)
    date_hierarchy = "created_at"
    ordering = ("name",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "organization", "created_at")
    list_filter = ("organization", "created_at")
    search_fields = ("name", "description", "organization__name")
    autocomplete_fields = ("organization",)
    ordering = ("organization__name", "name")


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "user", "role", "status", "department", "position", "joined_at")
    list_filter = ("role", "status", "organization", "department")
    search_fields = (
        "organization__name",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "position",
    )
    autocomplete_fields = ("organization", "user", "department", "invited_by")
    date_hierarchy = "created_at"
    ordering = ("organization__name", "user__username")


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "email",
        "role",
        "status",
        "department",
        "position",
        "date_reception",
        "invited_by",
        "expires_at",
        "created_at",
    )
    list_filter = ("role", "status", "organization", "department", "created_at", "expires_at")
    search_fields = ("organization__name", "email", "token", "invited_by__username", "invited_by__email", "position")
    autocomplete_fields = ("organization", "department", "invited_by")
    readonly_fields = ("token", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
