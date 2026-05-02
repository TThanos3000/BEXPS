import json

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FileUploadForm, LocationForm
from .models import Equipment, EquipmentType, File, Location, LocationModel


def _get_building_location(building_id: int) -> Location:
    return get_object_or_404(
        Location,
        id=building_id,
        location_type=Location.LocationType.BUILDING,
    )


def building_list(request):
    buildings = (
        Location.objects
        .filter(location_type=Location.LocationType.BUILDING)
        .select_related("organization", "parent")
        .order_by("name")
    )
    return render(request, "building_list.html", {"buildings": buildings})


def building_detail(request, building_id: int):
    building = _get_building_location(building_id)

    q = (request.GET.get("q") or "").strip()

    locations_qs = (
        Location.objects
        .filter(parent=building)
        .select_related("parent", "organization")
        .order_by("name")
    )

    if q:
        locations_qs = locations_qs.filter(name__icontains=q).order_by("id")

    return render(
        request,
        "building_detail.html",
        {
            "building": building,
            "locations": list(locations_qs),
            "q": q,
        },
    )


def location_detail(request, building_id: int, location_id: int):
    building = _get_building_location(building_id)
    location = get_object_or_404(Location, id=location_id)

    models = (
        LocationModel.objects
        .filter(location=location)
        .order_by("-created_at")
    )
    files = (
        File.objects
        .filter(Q(organization=location.organization) | Q(organization__isnull=True))
        .order_by("-created_at")
    )

    return render(
        request,
        "location_detail.html",
        {
            "building": building,
            "location": location,
            "models": models,
            "files": files,
        },
    )


def location_create(request, building_id):
    building = _get_building_location(building_id)

    if request.method == "POST":
        form = LocationForm(request.POST)
        if form.is_valid():
            loc = form.save(commit=False)
            loc.organization = building.organization
            if loc.parent is None:
                loc.parent = building
            loc.save()
            messages.success(request, "Локация создана")
            return redirect("parmodels:building_detail", building_id=building.id)
    else:
        form = LocationForm(initial={"parent": building})

    if "parent" in form.fields:
        form.fields["parent"].queryset = (
            Location.objects
            .filter(Q(organization=building.organization) | Q(id=building.id))
            .order_by("location_type", "name")
        )

    return render(request, "location_form.html", {
        "building": building,
        "form": form,
        "mode": "create",
    })


def location_edit(request, building_id, location_id):
    building = _get_building_location(building_id)
    location = get_object_or_404(Location, id=location_id)

    if request.method == "POST":
        form = LocationForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            messages.success(request, "Локация обновлена")
            return redirect("parmodels:location_detail", building_id=building.id, location_id=location.id)
    else:
        form = LocationForm(instance=location)

    if "parent" in form.fields:
        form.fields["parent"].queryset = (
            Location.objects
            .filter(Q(organization=building.organization) | Q(id=building.id))
            .exclude(id=location.id)
            .order_by("location_type", "name")
        )

    return render(request, "location_form.html", {
        "building": building,
        "location": location,
        "form": form,
        "mode": "edit",
    })


def ifc_model_upload(request, building_id: int, location_id: int):
    building = _get_building_location(building_id)
    location = get_object_or_404(Location, id=location_id)

    if request.method == "POST":
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.organization = location.organization
            obj.file_type = "ifc"
            if obj.file_path:
                obj.file_size = obj.file_path.size
            obj.save()
            messages.success(request, "Файл загружен")
            return redirect("parmodels:location_detail", building_id=building.id, location_id=location.id)
    else:
        form = FileUploadForm()

    return render(
        request,
        "ifc_model_upload.html",
        {"building": building, "location": location, "form": form},
    )


def ifc_model_delete(request, building_id: int, location_id: int, ifc_model_id: int):
    building = _get_building_location(building_id)
    location = get_object_or_404(Location, id=location_id)
    obj = get_object_or_404(LocationModel, id=ifc_model_id, location=location)

    name = obj.name
    obj.delete()

    messages.success(request, f"Удалено: {name}")
    return redirect("parmodels:location_detail", building_id=building.id, location_id=location.id)


def ifc_ingest_json(request, building_id: int, location_id: int, ifc_id: int):
    if request.content_type != "application/json":
        return HttpResponseBadRequest("Expected application/json")

    building = _get_building_location(building_id)
    location = get_object_or_404(Location, id=location_id)
    file_obj = get_object_or_404(File, id=ifc_id)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    model = LocationModel.objects.create(
        location=location,
        name=file_obj.file_name,
        model_json=payload,
    )

    return JsonResponse(
        {"ok": True, "created": 1, "model_id": model.id, "building_id": building.id}
    )


def location_equipment(request, building_id: int, location_id: int):
    building = _get_building_location(building_id)
    location = get_object_or_404(Location, pk=location_id)

    equipments = (
        Equipment.objects
        .filter(location=location)
        .select_related("status", "type_equipment", "organization", "location")
        .order_by("name_equipment", "inventory_number")
    )

    q = (request.GET.get("q") or "").strip()
    if q:
        equipments = equipments.filter(
            Q(name_equipment__icontains=q)
            | Q(inventory_number__icontains=q)
            | Q(external_id__icontains=q)
            | Q(type_equipment__name__icontains=q)
            | Q(status__name__icontains=q)
        )

    type_code = (request.GET.get("type") or "").strip()
    if type_code:
        equipments = equipments.filter(type_equipment__code=type_code)

    type_choices = (
        EquipmentType.objects
        .filter(equipment__location=location)
        .distinct()
        .order_by("code")
    )

    context = {
        "building": building,
        "location": location,
        "equipments": equipments,
        "q": q,
        "type_code": type_code,
        "type_choices": type_choices,
    }
    return render(request, "location_equipment.html", context)
