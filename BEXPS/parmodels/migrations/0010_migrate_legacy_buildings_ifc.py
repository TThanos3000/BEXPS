from django.db import migrations


def forwards(apps, schema_editor):
    Building = apps.get_model("parmodels", "Building")
    Location = apps.get_model("parmodels", "Location")
    IfcModel = apps.get_model("parmodels", "IfcModel")
    ModelElement = apps.get_model("parmodels", "ModelElement")
    File = apps.get_model("parmodels", "File")
    LocationModel = apps.get_model("parmodels", "LocationModel")

    roots_by_building_id = {}

    for building in Building.objects.all().order_by("id"):
        root = (
            Location.objects
            .filter(
                building_id=building.id,
                parent__isnull=True,
                location_type="building",
                name=building.name,
            )
            .first()
        )
        if root is None:
            root = Location.objects.create(
                building_id=building.id,
                name=building.name,
                location_type="building",
                description=building.description or "",
                address_location=building.address or "",
            )
        else:
            updates = []
            if not root.description and building.description:
                root.description = building.description
                updates.append("description")
            if not root.address_location and building.address:
                root.address_location = building.address
                updates.append("address_location")
            if updates:
                root.save(update_fields=updates)

        roots_by_building_id[building.id] = root

        (
            Location.objects
            .filter(building_id=building.id, parent__isnull=True)
            .exclude(id=root.id)
            .update(parent_id=root.id)
        )

    for ifc_model in IfcModel.objects.select_related("location").all().order_by("id"):
        file_obj = None
        if ifc_model.ifc_file:
            file_obj = File.objects.create(
                organization=ifc_model.location.organization,
                file_name=ifc_model.model_name,
                file_path=ifc_model.ifc_file.name,
                file_type="ifc",
            )

        elements = []
        for element in (
            ModelElement.objects
            .filter(ifc_model_id=ifc_model.id)
            .select_related("element_type")
            .order_by("id")
        ):
            elements.append(
                {
                    "ifcId": element.ifc_id,
                    "globalId": element.global_id,
                    "name": element.name,
                    "ifcType": element.element_type.code if element.element_type_id else None,
                    "type": element.element_type.ru_name if element.element_type_id else None,
                    "raw": element.raw,
                }
            )

        LocationModel.objects.create(
            location_id=ifc_model.location_id,
            name=ifc_model.model_name,
            model_json={
                "meta": {
                    "legacyIfcModelId": ifc_model.id,
                    "fileId": file_obj.id if file_obj else None,
                    "fileName": ifc_model.ifc_file.name if ifc_model.ifc_file else None,
                    "sha256": ifc_model.ifc_sha256,
                    "status": ifc_model.status,
                    "isParsed": ifc_model.is_parsed,
                },
                "elements": elements,
            },
        )


def backwards(apps, schema_editor):
    # Legacy data is intentionally not reconstructed from Location/LocationModel.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("parmodels", "0009_file_history_application_history_equipment"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
