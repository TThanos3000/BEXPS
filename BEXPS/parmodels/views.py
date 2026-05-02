import json

from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    ApplicationForm,
    ApplicationStatusForm,
    EquipmentForm,
    EquipmentStatusForm,
    FileUploadForm,
    LocationForm,
    LocationModelForm,
)
from .models import (
    Application,
    ApplicationStatus,
    Equipment,
    EquipmentStatus,
    EquipmentType,
    File,
    History_Application,
    History_Equipment,
    Location,
    LocationModel,
    OrganizationMembership,
)


def _get_building_location(building_id: int) -> Location:
    return get_object_or_404(
        Location,
        id=building_id,
        location_type=Location.LocationType.BUILDING,
    )


def _flatten_locations(locations):
    by_parent = {}
    by_id = {}
    for location in locations:
        by_id[location.id] = location
        by_parent.setdefault(location.parent_id, []).append(location)

    flat = []
    visited = set()

    def visit(node, level):
        if node.id in visited:
            return
        visited.add(node.id)
        flat.append({"location": node, "level": level})
        for child in by_parent.get(node.id, []):
            visit(child, level + 1)

    for root in by_parent.get(None, []):
        visit(root, 0)

    for location in locations:
        if location.id not in visited:
            level = 0
            parent = location.parent
            while parent and parent.id in by_id:
                level += 1
                parent = parent.parent
            visit(location, level)

    return flat


def _location_tree_rows(locations):
    by_parent = {}
    by_id = {}
    for location in locations:
        by_id[location.id] = location
        by_parent.setdefault(location.parent_id, []).append(location)

    rows = []
    visited = set()

    def add_row(location, level):
        if location.id in visited:
            return
        visited.add(location.id)
        rows.append(
            {
                "location": location,
                "level": level,
                "has_children": bool(by_parent.get(location.id)),
                "parent_id": location.parent_id if location.parent_id in by_id else None,
            }
        )
        for child in by_parent.get(location.id, []):
            add_row(child, level + 1)

    for root in by_parent.get(None, []):
        add_row(root, 0)

    for location in locations:
        if location.id not in visited:
            add_row(location, 0)

    return rows


def _location_descendant_ids(location):
    ids = []
    queue = [location.id]

    while queue:
        child_ids = list(
            Location.objects
            .filter(parent_id__in=queue)
            .values_list("id", flat=True)
        )
        if not child_ids:
            break
        ids.extend(child_ids)
        queue = child_ids

    return ids


def _get_current_organization(user):
    if not user.is_authenticated:
        return None
    membership = (
        OrganizationMembership.objects
        .filter(user=user, status=OrganizationMembership.Status.ACTIVE)
        .select_related("organization")
        .order_by("id")
        .first()
    )
    if membership:
        return membership.organization
    return None


@login_required
def building_list(request):
    buildings = (
        Location.objects
        .filter(location_type=Location.LocationType.BUILDING)
        .select_related("organization", "parent")
        .order_by("name")
    )
    User = get_user_model()
    completed_status_codes = ("done", "completed", "closed", "finished")

    context = {
        "buildings": buildings,
        "applications_count": Application.objects.count(),
        "active_applications_count": Application.objects.exclude(
            status__code__in=completed_status_codes
        ).count(),
        "completed_applications_count": Application.objects.filter(
            status__code__in=completed_status_codes
        ).count(),
        "locations_count": Location.objects.count(),
        "equipment_count": Equipment.objects.count(),
        "users_count": User.objects.count(),
    }
    return render(request, "building_list.html", context)


@login_required
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


@login_required
def applications_list(request):
    q = (request.GET.get("q") or "").strip()
    applications = (
        Application.objects
        .select_related("organization", "location", "equipment", "executor", "priority", "status")
        .order_by("-created_at")
    )

    if q:
        applications = applications.filter(
            Q(name_application__icontains=q)
            | Q(about__icontains=q)
        )

    statuses = ApplicationStatus.objects.order_by("name", "code")
    status_groups = [
        {
            "status": status,
            "count": applications.filter(status=status).count(),
        }
        for status in statuses
    ]
    unassigned_count = applications.filter(status__isnull=True).count()

    return render(
        request,
        "applications_list.html",
        {
            "applications": applications,
            "statuses": statuses,
            "status_groups": status_groups,
            "unassigned_count": unassigned_count,
            "q": q,
        },
    )


@login_required
def application_detail(request, application_id: int):
    application = get_object_or_404(
        Application.objects.select_related(
            "organization",
            "location",
            "equipment",
            "creator",
            "executor",
            "priority",
            "status",
        ),
        id=application_id,
    )
    history = (
        History_Application.objects
        .filter(application=application)
        .select_related("user", "status_old", "status_new", "file")
        .order_by("-changed_at")
    )
    status_form = ApplicationStatusForm(
        statuses=ApplicationStatus.objects.filter(is_active=True).order_by("name", "code"),
        initial={"status": application.status},
    )
    return render(
        request,
        "application_detail.html",
        {
            "application": application,
            "history": history,
            "status_form": status_form,
        },
    )


@login_required
def application_create(request):
    current_organization = _get_current_organization(request.user)

    if request.method == "POST":
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.creator = request.user
            application.date_create = timezone.now()
            if application.organization is None:
                application.organization = current_organization
            application.save()
            messages.success(request, "Заявка создана")
            return redirect("parmodels:application_detail", application_id=application.id)
    else:
        form = ApplicationForm(initial={"organization": current_organization})

    return render(
        request,
        "application_form.html",
        {
            "form": form,
            "title": "Новая заявка",
            "cancel_url": "parmodels:applications_list",
        },
    )


@login_required
@require_POST
def application_status_update(request, application_id: int):
    application = get_object_or_404(
        Application.objects.select_related("organization", "status"),
        id=application_id,
    )
    old_status = application.status
    form = ApplicationStatusForm(
        request.POST,
        statuses=ApplicationStatus.objects.filter(is_active=True).order_by("name", "code"),
    )

    if form.is_valid():
        new_status = form.cleaned_data["status"]
        if old_status_id := getattr(old_status, "id", None):
            status_changed = old_status_id != new_status.id
        else:
            status_changed = new_status is not None

        if status_changed:
            application.status = new_status
            application.save(update_fields=["status", "updated_at"])
            History_Application.objects.create(
                organization=application.organization,
                application=application,
                user=request.user,
                status_old=old_status,
                status_new=new_status,
                comment=form.cleaned_data["comment"],
            )
            messages.success(request, "Статус заявки обновлен")
        else:
            messages.info(request, "Статус заявки не изменился")
    else:
        messages.error(request, "Не удалось обновить статус заявки")

    return redirect("parmodels:application_detail", application_id=application.id)


@login_required
def locations_list(request):
    q = (request.GET.get("q") or "").strip()
    locations = (
        Location.objects
        .select_related("organization", "parent", "parent__parent")
        .annotate(equipment_count=Count("equipment"))
        .order_by("parent_id", "location_type", "name")
    )

    if q:
        locations = locations.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(location_type__icontains=q)
        )

    return render(
        request,
        "locations_list.html",
        {
            "location_nodes": _location_tree_rows(list(locations)),
            "q": q,
        },
    )


@login_required
def location_detail_standalone(request, location_id: int):
    location = get_object_or_404(
        Location.objects.select_related("organization", "parent"),
        id=location_id,
    )
    children = (
        Location.objects
        .filter(parent=location)
        .select_related("organization", "parent")
        .order_by("location_type", "name")
    )
    equipment = (
        Equipment.objects
        .filter(location=location)
        .select_related("status", "type_equipment")
        .order_by("name_equipment", "inventory_number")
    )
    return render(
        request,
        "location_detail_standalone.html",
        {
            "location": location,
            "children": children,
            "location_models": location.location_models.order_by("-created_at"),
            "equipment": equipment,
        },
    )


@login_required
def location_create_standalone(request):
    current_organization = _get_current_organization(request.user)

    if request.method == "POST":
        form = LocationForm(request.POST)
        if form.is_valid():
            location = form.save(commit=False)
            if location.organization is None:
                location.organization = current_organization
            location.save()
            messages.success(request, "Локация создана")
            return redirect("parmodels:location_detail_standalone", location_id=location.id)
    else:
        form = LocationForm(initial={"organization": current_organization})

    if "parent" in form.fields:
        form.fields["parent"].required = False
        form.fields["parent"].queryset = Location.objects.select_related("organization").order_by(
            "organization__name", "location_type", "name"
        )

    return render(
        request,
        "location_form.html",
        {
            "form": form,
            "mode": "create",
            "title": "Новая локация",
            "cancel_url": "parmodels:locations_list",
        },
    )


@login_required
def location_model_create(request, location_id: int):
    location = get_object_or_404(
        Location.objects.select_related("organization", "parent"),
        id=location_id,
    )

    if request.method == "POST":
        form = LocationModelForm(request.POST)
        if form.is_valid():
            location_model = form.save(commit=False)
            location_model.location = location
            location_model.save()
            messages.success(request, "Техплан добавлен")
            return redirect("parmodels:location_detail_standalone", location_id=location.id)
    else:
        form = LocationModelForm(
            initial={
                "name": f"Техплан: {location.name}",
                "model_json": json.dumps(
                    {"objects": [], "metadata": {"source": "manual"}},
                    ensure_ascii=False,
                    indent=2,
                ),
            }
        )

    return render(
        request,
        "location_model_form.html",
        {
            "location": location,
            "form": form,
        },
    )


@login_required
def equipment_list(request):
    q = (request.GET.get("q") or "").strip()
    equipment = (
        Equipment.objects
        .select_related("organization", "location", "status", "type_equipment")
        .order_by("name_equipment", "inventory_number")
    )

    if q:
        equipment = equipment.filter(
            Q(name_equipment__icontains=q)
            | Q(inventory_number__icontains=q)
            | Q(external_id__icontains=q)
        )

    statuses = EquipmentStatus.objects.order_by("name", "code")
    types = EquipmentType.objects.order_by("name", "code")
    status_groups = [
        {"status": status, "count": equipment.filter(status=status).count()}
        for status in statuses
    ]
    type_groups = [
        {"type": equipment_type, "count": equipment.filter(type_equipment=equipment_type).count()}
        for equipment_type in types
    ]

    return render(
        request,
        "equipment_list.html",
        {
            "equipment": equipment,
            "statuses": statuses,
            "types": types,
            "status_groups": status_groups,
            "type_groups": type_groups,
            "unassigned_status_count": equipment.filter(status__isnull=True).count(),
            "unassigned_type_count": equipment.filter(type_equipment__isnull=True).count(),
            "q": q,
        },
    )


@login_required
def equipment_detail(request, equipment_id: int):
    equipment = get_object_or_404(
        Equipment.objects.select_related("organization", "location", "status", "type_equipment"),
        id=equipment_id,
    )
    history = (
        History_Equipment.objects
        .filter(equipment=equipment)
        .select_related("user", "application", "file")
        .order_by("-performed_at", "-id")
    )
    status_form = EquipmentStatusForm(
        statuses=EquipmentStatus.objects.filter(is_active=True).order_by("name", "code"),
        applications=Application.objects.filter(
            Q(equipment=equipment) | Q(equipment__isnull=True)
        ).select_related("status").order_by("-created_at"),
        initial={"status": equipment.status},
    )
    return render(
        request,
        "equipment_detail.html",
        {
            "equipment": equipment,
            "history": history,
            "status_form": status_form,
        },
    )


@login_required
def equipment_create(request):
    current_organization = _get_current_organization(request.user)

    if request.method == "POST":
        form = EquipmentForm(request.POST)
        if form.is_valid():
            equipment = form.save(commit=False)
            if equipment.organization is None:
                equipment.organization = current_organization
            equipment.save()
            messages.success(request, "Оборудование создано")
            return redirect("parmodels:equipment_detail", equipment_id=equipment.id)
    else:
        form = EquipmentForm(initial={"organization": current_organization})

    return render(
        request,
        "equipment_form.html",
        {
            "form": form,
            "title": "Новое оборудование",
            "cancel_url": "parmodels:equipment_list",
        },
    )


@login_required
@require_POST
def equipment_status_update(request, equipment_id: int):
    equipment = get_object_or_404(
        Equipment.objects.select_related("organization", "status"),
        id=equipment_id,
    )
    old_status = equipment.status
    form = EquipmentStatusForm(
        request.POST,
        statuses=EquipmentStatus.objects.filter(is_active=True).order_by("name", "code"),
        applications=Application.objects.filter(
            Q(equipment=equipment) | Q(equipment__isnull=True)
        ).order_by("-created_at"),
    )

    if form.is_valid():
        new_status = form.cleaned_data["status"]
        if old_status_id := getattr(old_status, "id", None):
            status_changed = old_status_id != new_status.id
        else:
            status_changed = new_status is not None

        if status_changed:
            equipment.status = new_status
            equipment.save(update_fields=["status", "updated_at"])
            History_Equipment.objects.create(
                organization=equipment.organization,
                equipment=equipment,
                application=form.cleaned_data["application"],
                user=request.user,
                maintenance_type=form.cleaned_data["maintenance_type"],
                description=form.cleaned_data["description"],
                result=form.cleaned_data["result"],
                performed_at=timezone.now(),
            )
            messages.success(request, "Статус оборудования обновлен")
        else:
            messages.info(request, "Статус оборудования не изменился")
    else:
        messages.error(request, "Не удалось обновить статус оборудования")

    return redirect("parmodels:equipment_detail", equipment_id=equipment.id)


@login_required
def application_delete_confirm(request, application_id: int):
    application = get_object_or_404(Application, id=application_id)
    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": application.name_application,
            "object_type": "заявку",
            "delete_url": "parmodels:application_delete",
            "object_id": application.id,
            "cancel_url": "parmodels:application_detail",
        },
    )


@login_required
@require_POST
def application_delete(request, application_id: int):
    application = get_object_or_404(Application, id=application_id)
    name = application.name_application
    application.delete()
    messages.success(request, f"Заявка удалена: {name}")
    return redirect("parmodels:applications_list")


@login_required
def equipment_delete_confirm(request, equipment_id: int):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": equipment.name_equipment,
            "object_type": "оборудование",
            "delete_url": "parmodels:equipment_delete",
            "object_id": equipment.id,
            "cancel_url": "parmodels:equipment_detail",
        },
    )


@login_required
@require_POST
def equipment_delete(request, equipment_id: int):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    name = equipment.name_equipment
    equipment.delete()
    messages.success(request, f"Оборудование удалено: {name}")
    return redirect("parmodels:equipment_list")


@login_required
def location_delete_confirm(request, location_id: int):
    location = get_object_or_404(Location, id=location_id)
    descendant_count = len(_location_descendant_ids(location))
    return render(
        request,
        "confirm_delete.html",
        {
            "object_name": location.name,
            "object_type": "локацию",
            "delete_url": "parmodels:location_delete",
            "object_id": location.id,
            "cancel_url": "parmodels:location_detail_standalone",
            "extra_warning": (
                f"Вместе с ней будут удалены дочерние локации: {descendant_count}."
                if descendant_count
                else ""
            ),
        },
    )


@login_required
@require_POST
def location_delete(request, location_id: int):
    location = get_object_or_404(Location, id=location_id)
    name = location.name
    descendant_ids = _location_descendant_ids(location)
    ids_to_delete = descendant_ids + [location.id]

    with transaction.atomic():
        Location.objects.filter(id__in=ids_to_delete).delete()

    messages.success(request, f"Локация удалена: {name}")
    return redirect("parmodels:locations_list")


@login_required
def users_list(request):
    User = get_user_model()
    q = (request.GET.get("q") or "").strip()
    users = (
        User.objects
        .prefetch_related(
            "organization_memberships__organization",
            "organization_memberships__department",
        )
        .order_by("last_name", "first_name", "email")
    )

    if q:
        users = users.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
            | Q(username__icontains=q)
        )

    return render(request, "users_list.html", {"users": users, "q": q})


@login_required
def user_detail(request, user_id: int):
    User = get_user_model()
    user_obj = get_object_or_404(
        User.objects.prefetch_related(
            "organization_memberships__organization",
            "organization_memberships__department",
        ),
        id=user_id,
    )
    return render(request, "user_detail.html", {"user_obj": user_obj})


@login_required
def profile(request):
    memberships = (
        OrganizationMembership.objects
        .filter(user=request.user)
        .select_related("organization", "department")
        .order_by("organization__name", "department__name")
    )
    return render(request, "profile.html", {"memberships": memberships})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("parmodels:login")


@login_required
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
    equipment = (
        Equipment.objects
        .filter(location=location)
        .select_related("status", "type_equipment")
        .order_by("name_equipment", "inventory_number")
    )

    return render(
        request,
        "location_detail.html",
        {
            "building": building,
            "location": location,
            "models": models,
            "files": files,
            "equipment": equipment,
        },
    )


@login_required
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
        form = LocationForm(initial={"organization": building.organization, "parent": building})

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
        "title": "Новая локация",
        "cancel_url": "parmodels:building_detail",
    })


@login_required
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
        "title": "Редактирование локации",
        "cancel_url": "parmodels:building_detail",
    })


@login_required
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


@login_required
@require_POST
def ifc_model_delete(request, building_id: int, location_id: int, ifc_model_id: int):
    building = _get_building_location(building_id)
    location = get_object_or_404(Location, id=location_id)
    obj = get_object_or_404(LocationModel, id=ifc_model_id, location=location)

    name = obj.name
    obj.delete()

    messages.success(request, f"Удалено: {name}")
    return redirect("parmodels:location_detail", building_id=building.id, location_id=location.id)


@login_required
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


@login_required
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
