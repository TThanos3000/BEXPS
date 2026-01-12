from django.shortcuts import get_object_or_404, render
from .models import Building, Location, IfcModel


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
