from django.contrib import admin
from .models import Building, Location, IfcModel, ElementType, ModelElement, User


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "address")
    search_fields = ("name", "address")
    ordering = ("id",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location_type", "building", "parent")
    list_filter = ("building", "location_type")
    search_fields = ("name", "building__name")
    autocomplete_fields = ("building", "parent")
    ordering = ("building_id", "id")


@admin.register(IfcModel)
class IfcModelAdmin(admin.ModelAdmin):
    list_display = ("id", "model_name", "status", "building", "location", "uploaded_at", "ifc_sha256_short")
    list_filter = ("status", "building")
    search_fields = ("model_name", "ifc_sha256", "building__name", "location__name")
    autocomplete_fields = ("building", "location")
    date_hierarchy = "uploaded_at"
    ordering = ("-uploaded_at",)

    @admin.display(description="sha256")
    def ifc_sha256_short(self, obj: IfcModel) -> str:
        return (obj.ifc_sha256[:10] + "…") if obj.ifc_sha256 else ""


@admin.register(ElementType)
class ElementTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "ru_name")
    search_fields = ("code", "ru_name")
    ordering = ("code",)


@admin.register(ModelElement)
class ModelElementAdmin(admin.ModelAdmin):
    list_display = ("id", "element_type", "global_id", "name", "ifc_model", "created_at")
    list_filter = ("element_type", "ifc_model")
    search_fields = ("global_id", "name", "element_type__code", "element_type__ru_name", "ifc_model__model_name")
    autocomplete_fields = ("ifc_model", "element_type")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    # Чтобы не грузить raw на список (в форме останется)
    exclude = ()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "last_name", "first_name", "email", "role")
    list_filter = ("role",)
    search_fields = ("last_name", "first_name", "email")
    ordering = ("last_name", "first_name")