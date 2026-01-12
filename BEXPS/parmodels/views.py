from django.contrib import messages
import json

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from .models import Building, Location, IfcModel
from .forms import IfcModelUploadForm
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest

from .models import IfcModel, ModelElement, ElementType  # подстрой под свои названия


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


def ifc_ingest_json(request, building_id: int, location_id: int, ifc_id: int):
    if request.content_type != "application/json":
        return HttpResponseBadRequest("Expected application/json")

    ifc_model = get_object_or_404(
        IfcModel,
        id=ifc_id,
        location_id=location_id,
        location__building_id=building_id,
    )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    elements = (payload or {}).get("elements") or {}

    # ожидаем ключи: walls, slabs, doors, windows
    # каждый элемент: ifcId, globalId, name, type, ifcType

    # если хочешь “перезаписывать” элементы при повторном парсинге:
    # ModelElement.objects.filter(ifc_model=ifc_model).delete()

    to_create = []

    with transaction.atomic():
        # маппинг "ifcType" -> русское название/группа (можешь хранить как ElementType)
        # если ElementType у тебя уже есть, оставь get_or_create
        for group_key, items in elements.items():
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue

                ifc_type = item.get("ifcType")  # например "IFCWALL"
                type_ru = item.get("type")  # например "Стена"

                element_type, _ = ElementType.objects.get_or_create(
                    code=ifc_type,
                    defaults={"ru_name": type_ru or ifc_type},
                )

                to_create.append(
                    ModelElement(
                        ifc_model=ifc_model,
                        element_type=element_type,
                        ifc_id=item.get("ifcId"),
                        global_id=item.get("globalId"),
                        name=item.get("name"),
                        # сюда позже можно добавить property_sets=...
                    )
                )

        ifc_model.is_parsed = True
        ifc_model.save(update_fields=["is_parsed"])

        if to_create:
            ModelElement.objects.bulk_create(to_create, batch_size=1000)

        # если хочешь пометить модель “распарсена”
        # ifc_model.is_parsed = True
        # ifc_model.save(update_fields=["is_parsed"])

    return JsonResponse(
        {"ok": True, "created": len(to_create)}
    )


def location_equipment(request, building_id: int, location_id: int):
    building = get_object_or_404(Building, pk=building_id)
    location = get_object_or_404(Location, pk=location_id, building=building)

    # 선택: показываем элементы конкретной IFC-модели (если выбрали), иначе последней
    ifc_models_qs = IfcModel.objects.filter(location=location).order_by("-id")

    selected_ifc_id = request.GET.get("ifc")
    if selected_ifc_id:
        selected_ifc_model = get_object_or_404(IfcModel, pk=selected_ifc_id, location=location)
    else:
        selected_ifc_model = ifc_models_qs.first()

    elements = ModelElement.objects.none()
    if selected_ifc_model:
        elements = (
            ModelElement.objects
            .filter(ifc_model=selected_ifc_model)
            .select_related("element_type", "ifc_model")
            .order_by("element_type__code", "name", "ifc_id")
        )

    # поиск по имени / globalId / ifcId / типу
    q = (request.GET.get("q") or "").strip()
    if q and selected_ifc_model:
        elements = elements.filter(
            Q(name__icontains=q)
            | Q(global_id__icontains=q)
            | Q(ifc_id__icontains=q)
            | Q(element_type__code__icontains=q)
            | Q(element_type__ru_name__icontains=q)
        )

    # фильтр по типу
    type_code = (request.GET.get("type") or "").strip()
    if type_code and selected_ifc_model:
        elements = elements.filter(element_type__code=type_code)

    type_choices = (
        ElementType.objects
        .filter(elements__ifc_model__location=location)
        .distinct()
        .order_by("code")
    )

    context = {
        "building": building,
        "location": location,
        "ifc_models": ifc_models_qs,
        "selected_ifc_model": selected_ifc_model,
        "elements": elements,
        "q": q,
        "type_code": type_code,
        "type_choices": type_choices,
    }
    return render(request, "location_equipment.html", context)