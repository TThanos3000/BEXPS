from django.contrib import messages

from django.shortcuts import get_object_or_404, redirect, render
from .models import Building, Location, IfcModel
from .forms import IfcModelUploadForm

def building_list(request):
    buildings = Building.objects.all().order_by("name")
    return render(request, "building_list.html", {"buildings": buildings})


def building_detail(request, building_id: int):
    building = get_object_or_404(Building, id=building_id)

    locations = (
        Location.objects
        .filter(building=building)
        .select_related("parent")
        .order_by("id")
    )

    models = (
        IfcModel.objects
        .filter(building=building)
        .select_related("location")
        .order_by("-uploaded_at")
    )

    return render(
        request,
        "building_detail.html",
        {
            "building": building,
            "locations": locations,
            "models": models,
        },
    )


def location_detail(request, building_id: int, location_id: int):
    building = get_object_or_404(Building, id=building_id)
    location = get_object_or_404(Location, id=location_id, building=building)

    models = (
        IfcModel.objects
        .filter(building=building, location=location)
        .order_by("-uploaded_at")
    )

    return render(
        request,
        "location_detail.html",
        {"building": building, "location": location, "models": models},
    )


def ifc_model_upload(request, building_id: int, location_id: int):
    building = get_object_or_404(Building, id=building_id)
    location = get_object_or_404(Location, id=location_id, building=building)

    if request.method == "POST":
        form = IfcModelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.building = building
            obj.location = location
            obj.status = "uploaded"
            obj.save()
            return redirect("parmodels:location_detail", building_id=building.id, location_id=location.id)
    else:
        form = IfcModelUploadForm()

    return render(
        request,
        "ifc_model_upload.html",
        {"building": building, "location": location, "form": form},
    )

def ifc_model_delete(request, building_id: int, location_id: int, ifc_model_id: int):
    building = get_object_or_404(Building, id=building_id)
    location = get_object_or_404(Location, id=location_id, building=building)
    obj = get_object_or_404(IfcModel, id=ifc_model_id, building=building, location=location)

    name = obj.model_name

    # 1) удалить файл (если есть)
    if obj.ifc_file:
        obj.ifc_file.delete(save=False)

    # 2) удалить запись
    obj.delete()

    messages.success(request, f"Удалено: {name}")
    return redirect("parmodels:location_detail", building_id=building.id, location_id=location.id)