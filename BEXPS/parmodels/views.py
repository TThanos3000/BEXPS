import json
import re
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    ApplicationEditForm,
    ApplicationForm,
    ApplicationStatusForm,
    EquipmentEditForm,
    EquipmentForm,
    EquipmentStatusForm,
    InvitationRegistrationForm,
    LocationForm,
    LocationModelForm,
    OrganizationInvitationForm,
    UserProfileForm,
)
from .models import (
    Application,
    ApplicationPriority,
    ApplicationStatus,
    Department,
    Equipment,
    EquipmentStatus,
    EquipmentType,
    History_Application,
    History_Equipment,
    Location,
    LocationModel,
    OrganizationInvitation,
    OrganizationMembership,
)
from .permissions import permission_flags, require_permission
from .services import (
    CURRENT_ORGANIZATION_SESSION_KEY,
    get_current_membership,
    get_current_organization as service_get_current_organization,
)

STATUS_FALLBACK_LABELS = {
    "new": "Новая",
    "in_progress": "В работе",
    "waiting_review": "Ожидает проверки",
    "completed": "Выполнена",
    "cancelled": "Отменена",
}
DEFAULT_BADGE_COLOR = "#6c757d"


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


def _get_current_organization(request):
    return service_get_current_organization(request.user, request=request)


def _organization_access_denied(request):
    return render(request, "organization_no_access.html", status=403)


def _require_current_organization(request):
    organization = _get_current_organization(request)
    if organization is None:
        messages.error(
            request,
            "Не найдена активная организация пользователя. Создание записи невозможно.",
        )
    return organization


def _organization_users_queryset(organization):
    return (
        get_user_model().objects
        .filter(
            organization_memberships__organization=organization,
            organization_memberships__status=OrganizationMembership.Status.ACTIVE,
        )
        .distinct()
        .order_by("last_name", "first_name", "email", "username")
    )


def _parse_filter_date(value):
    if not value:
        return None
    return parse_date(value)


def _status_display(status):
    if not status:
        return "Без статуса"
    if status.name:
        return status.name
    return STATUS_FALLBACK_LABELS.get(status.code, status.code)


def _safe_color(color_code):
    if color_code and re.fullmatch(r"#[0-9a-fA-F]{6}", color_code):
        return color_code
    return DEFAULT_BADGE_COLOR


def _application_status_groups(queryset=None):
    base_queryset = queryset if queryset is not None else Application.objects.all()
    statuses = ApplicationStatus.objects.order_by("name", "code")
    groups = [
        {
            "status": status,
            "label": _status_display(status),
            "count": base_queryset.filter(status=status).count(),
            "color": _safe_color(getattr(status, "color_code", "")),
        }
        for status in statuses
    ]
    unassigned_count = base_queryset.filter(status__isnull=True).count()
    if unassigned_count:
        groups.append({"status": None, "label": "Без статуса", "count": unassigned_count, "color": DEFAULT_BADGE_COLOR})
    return groups


def _mark_deadline_state(applications):
    threshold = timezone.now() + timedelta(days=2)
    for application in applications:
        application.deadline_is_urgent = bool(
            application.deadline and application.deadline <= threshold
        )
        application.status_color = _safe_color(getattr(application.status, "color_code", ""))
        application.priority_color = _safe_color(getattr(application.priority, "color_code", ""))
    return applications


@login_required
def dashboard(request):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    completed_status_codes = ("done", "completed", "closed", "finished")
    applications = Application.objects.filter(organization=organization)

    context = {
        "current_organization": organization,
        **permission_flags(request.user, request=request),
        "applications_count": applications.count(),
        "active_applications_count": applications.exclude(
            status__code__in=completed_status_codes
        ).count(),
        "completed_applications_count": applications.filter(
            status__code__in=completed_status_codes
        ).count(),
        "locations_count": Location.objects.filter(organization=organization).count(),
        "equipment_count": Equipment.objects.filter(organization=organization).count(),
        "users_count": OrganizationMembership.objects.filter(
            organization=organization,
            status=OrganizationMembership.Status.ACTIVE,
        ).count(),
    }
    return render(request, "dashboard.html", context)


@login_required
def applications_list(request):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "applications.view", request=request)
    q = (request.GET.get("q") or "").strip()
    status_id = (request.GET.get("status") or "").strip()
    priority_id = (request.GET.get("priority") or "").strip()
    executor_id = (request.GET.get("executor") or "").strip()
    date_create_from = (request.GET.get("date_create_from") or "").strip()
    date_create_to = (request.GET.get("date_create_to") or "").strip()
    deadline_from = (request.GET.get("deadline_from") or "").strip()
    deadline_to = (request.GET.get("deadline_to") or "").strip()
    mine = (request.GET.get("mine") or "").strip() == "1"
    filter_errors = []
    date_create_from_date = _parse_filter_date(date_create_from)
    date_create_to_date = _parse_filter_date(date_create_to)
    deadline_from_date = _parse_filter_date(deadline_from)
    deadline_to_date = _parse_filter_date(deadline_to)
    invalid_deadline_range = bool(
        deadline_from
        and deadline_to
        and deadline_from_date
        and deadline_to_date
        and deadline_from_date > deadline_to_date
    )
    if invalid_deadline_range:
        filter_errors.append("Неверный диапазон дат")

    applications = (
        Application.objects
        .filter(organization=organization)
        .select_related("organization", "location", "equipment", "executor", "priority", "status")
        .order_by("-created_at")
    )

    if q:
        search_query = (
            Q(name_application__icontains=q)
            | Q(about__icontains=q)
        )
        if q.isdigit():
            search_query |= Q(id=int(q))
        applications = applications.filter(search_query)

    if status_id:
        applications = applications.filter(status_id=status_id)
    if priority_id:
        applications = applications.filter(priority_id=priority_id)
    if executor_id:
        applications = applications.filter(executor_id=executor_id)
    if mine:
        applications = applications.filter(executor=request.user)
    if date_create_from_date:
        applications = applications.filter(date_create__date__gte=date_create_from_date)
    if date_create_to_date:
        applications = applications.filter(date_create__date__lte=date_create_to_date)
    if not invalid_deadline_range:
        if deadline_from_date:
            applications = applications.filter(deadline__date__gte=deadline_from_date)
        if deadline_to_date:
            applications = applications.filter(deadline__date__lte=deadline_to_date)

    filtered_applications = applications
    current_membership = get_current_membership(request.user, request=request)
    completed_status_filter = Q(status__code="completed")
    completed_applications_qs = (
        Application.objects
        .filter(organization=organization)
        .filter(completed_status_filter)
        .select_related("organization", "location", "equipment", "executor", "priority", "status")
        .order_by("-created_at")
    )
    if current_membership and current_membership.role in (
        OrganizationMembership.Role.ENGINEER,
        OrganizationMembership.Role.CHIEF_ENGINEER,
    ):
        completed_applications_qs = completed_applications_qs.filter(executor=request.user)
        completed_applications_title = "Мои выполненные заявки"
    else:
        completed_applications_title = "Выполненные заявки"
    completed_applications = _mark_deadline_state(list(completed_applications_qs))
    applications = _mark_deadline_state(
        list(filtered_applications.exclude(completed_status_filter))
    )
    statuses = ApplicationStatus.objects.order_by("name", "code")
    priorities = ApplicationPriority.objects.order_by("weight", "name", "code")
    executors = _organization_users_queryset(organization)
    status_groups = _application_status_groups(filtered_applications)
    status_chart = {
        "labels": [group["label"] for group in status_groups],
        "counts": [group["count"] for group in status_groups],
        "colors": [group["color"] for group in status_groups],
    }

    return render(
        request,
        "applications_list.html",
        {
            "applications": applications,
            "completed_applications": completed_applications,
            "statuses": statuses,
            "priorities": priorities,
            "executors": executors,
            "status_groups": status_groups,
            "status_chart": status_chart,
            "q": q,
            "filter_errors": filter_errors,
            "completed_applications_title": completed_applications_title,
            **permission_flags(request.user, request=request),
            "filters": {
                "status": status_id,
                "priority": priority_id,
                "executor": executor_id,
                "mine": "1" if mine else "",
                "date_create_from": date_create_from,
                "date_create_to": date_create_to,
                "deadline_from": deadline_from,
                "deadline_to": deadline_to,
            },
        },
    )


@login_required
def application_detail(request, application_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "applications.view", request=request)
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
        organization=organization,
    )
    history = (
        History_Application.objects
        .filter(application=application, organization=organization)
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
            **permission_flags(request.user, request=request),
        },
    )


@login_required
def application_create(request):
    current_organization = _require_current_organization(request)
    if current_organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "applications.create", request=request)

    if request.method == "POST":
        form = ApplicationForm(request.POST, hide_organization=True, organization=current_organization)
        if form.is_valid():
            application = form.save(commit=False)
            application.creator = request.user
            application.date_create = timezone.now()
            application.organization = current_organization
            application.save()
            History_Application.objects.create(
                organization=application.organization,
                application=application,
                user=request.user,
                status_old=application.status,
                status_new=application.status,
                comment="Заявка создана",
            )
            messages.success(request, "Заявка создана")
            return redirect("parmodels:application_detail", application_id=application.id)
    else:
        form = ApplicationForm(hide_organization=True, organization=current_organization)

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
def application_edit(request, application_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "applications.update", request=request)
    application = get_object_or_404(
        Application.objects.select_related("organization", "status"),
        id=application_id,
        organization=organization,
    )
    old_status = application.status

    if request.method == "POST":
        form = ApplicationEditForm(
            request.POST,
            instance=application,
            hide_organization=True,
            organization=organization,
        )
        if form.is_valid():
            application = form.save()
            History_Application.objects.create(
                organization=application.organization,
                application=application,
                user=request.user,
                status_old=old_status,
                status_new=application.status,
                comment="Были внесены изменения",
            )
            messages.success(request, "Заявка обновлена")
            return redirect("parmodels:application_detail", application_id=application.id)
    else:
        form = ApplicationEditForm(instance=application, hide_organization=True, organization=organization)

    return render(
        request,
        "application_form.html",
        {
            "form": form,
            "title": "Редактирование заявки",
            "cancel_url": "parmodels:application_detail",
            "cancel_url_arg": application.id,
        },
    )


@login_required
@require_POST
def application_status_update(request, application_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "applications.update_status", request=request)
    application = get_object_or_404(
        Application.objects.select_related("organization", "status"),
        id=application_id,
        organization=organization,
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
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "locations.view", request=request)
    q = (request.GET.get("q") or "").strip()
    equipment_presence = (request.GET.get("equipment_presence") or "").strip()
    locations = (
        Location.objects
        .filter(organization=organization)
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

    if equipment_presence == "has_equipment":
        locations = locations.filter(equipment_count__gt=0)
    elif equipment_presence == "no_equipment":
        locations = locations.filter(equipment_count=0)

    return render(
        request,
        "locations_list.html",
        {
            "location_nodes": _location_tree_rows(list(locations)),
            "q": q,
            "equipment_presence": equipment_presence,
            **permission_flags(request.user, request=request),
        },
    )


@login_required
def location_detail_standalone(request, location_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "locations.view", request=request)
    location = get_object_or_404(
        Location.objects.select_related("organization", "parent"),
        id=location_id,
        organization=organization,
    )
    children = (
        Location.objects
        .filter(parent=location, organization=organization)
        .select_related("organization", "parent")
        .order_by("location_type", "name")
    )
    equipment = (
        Equipment.objects
        .filter(location=location, organization=organization)
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
            **permission_flags(request.user, request=request),
        },
    )


@login_required
def location_create_standalone(request):
    current_organization = _require_current_organization(request)
    if current_organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "locations.create", request=request)

    if request.method == "POST":
        form = LocationForm(request.POST, hide_organization=True, organization=current_organization)
        if form.is_valid():
            location = form.save(commit=False)
            location.organization = current_organization
            location.save()
            messages.success(request, "Локация создана")
            return redirect("parmodels:location_detail_standalone", location_id=location.id)
    else:
        form = LocationForm(hide_organization=True, organization=current_organization)

    if "parent" in form.fields:
        form.fields["parent"].required = False
        form.fields["parent"].queryset = Location.objects.filter(organization=current_organization).select_related("organization").order_by(
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
def location_edit_standalone(request, location_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "locations.update", request=request)
    location = get_object_or_404(Location, id=location_id, organization=organization)

    if request.method == "POST":
        form = LocationForm(request.POST, instance=location, hide_organization=True, organization=organization)
        if form.is_valid():
            location = form.save()
            messages.success(request, "Локация обновлена")
            return redirect("parmodels:location_detail_standalone", location_id=location.id)
    else:
        form = LocationForm(instance=location, hide_organization=True, organization=organization)

    if "parent" in form.fields:
        form.fields["parent"].required = False
        form.fields["parent"].queryset = (
            Location.objects
            .filter(organization=organization)
            .select_related("organization")
            .exclude(id=location.id)
            .order_by("organization__name", "location_type", "name")
        )

    return render(
        request,
        "location_form.html",
        {
            "form": form,
            "mode": "edit",
            "title": "Редактирование локации",
            "cancel_url": "parmodels:location_detail_standalone",
            "cancel_url_arg": location.id,
        },
    )


@login_required
def location_model_create(request, location_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "locations.update", request=request)
    location = get_object_or_404(
        Location.objects.select_related("organization", "parent"),
        id=location_id,
        organization=organization,
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
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "equipment.view", request=request)
    q = (request.GET.get("q") or "").strip()
    equipment = (
        Equipment.objects
        .filter(organization=organization)
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
            **permission_flags(request.user, request=request),
        },
    )


@login_required
def equipment_detail(request, equipment_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "equipment.view", request=request)
    equipment = get_object_or_404(
        Equipment.objects.select_related("organization", "location", "status", "type_equipment"),
        id=equipment_id,
        organization=organization,
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
            Q(equipment=equipment) | Q(equipment__isnull=True),
            organization=organization,
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
            **permission_flags(request.user, request=request),
        },
    )


@login_required
def equipment_create(request):
    current_organization = _require_current_organization(request)
    if current_organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "equipment.create", request=request)

    if request.method == "POST":
        form = EquipmentForm(request.POST, hide_organization=True, organization=current_organization)
        if form.is_valid():
            equipment = form.save(commit=False)
            equipment.organization = current_organization
            equipment.save()
            messages.success(request, "Оборудование создано")
            return redirect("parmodels:equipment_detail", equipment_id=equipment.id)
    else:
        form = EquipmentForm(hide_organization=True, organization=current_organization)

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
def equipment_edit(request, equipment_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "equipment.update", request=request)
    equipment = get_object_or_404(
        Equipment.objects.select_related("organization", "status"),
        id=equipment_id,
        organization=organization,
    )

    if request.method == "POST":
        form = EquipmentEditForm(
            request.POST,
            instance=equipment,
            hide_organization=True,
            organization=organization,
        )
        if form.is_valid():
            equipment = form.save()
            History_Equipment.objects.create(
                organization=equipment.organization,
                equipment=equipment,
                application=None,
                user=request.user,
                maintenance_type="Изменение данных",
                description="Были внесены изменения",
                result="Данные оборудования обновлены",
                performed_at=timezone.now(),
            )
            messages.success(request, "Оборудование обновлено")
            return redirect("parmodels:equipment_detail", equipment_id=equipment.id)
    else:
        form = EquipmentEditForm(instance=equipment, hide_organization=True, organization=organization)

    return render(
        request,
        "equipment_form.html",
        {
            "form": form,
            "title": "Редактирование оборудования",
            "cancel_url": "parmodels:equipment_detail",
            "cancel_url_arg": equipment.id,
        },
    )


@login_required
@require_POST
def equipment_status_update(request, equipment_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "equipment.update_status", request=request)
    equipment = get_object_or_404(
        Equipment.objects.select_related("organization", "status"),
        id=equipment_id,
        organization=organization,
    )
    old_status = equipment.status
    form = EquipmentStatusForm(
        request.POST,
        statuses=EquipmentStatus.objects.filter(is_active=True).order_by("name", "code"),
        applications=Application.objects.filter(
            Q(equipment=equipment) | Q(equipment__isnull=True),
            organization=organization,
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
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "applications.delete", request=request)
    application = get_object_or_404(Application, id=application_id, organization=organization)
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
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "applications.delete", request=request)
    application = get_object_or_404(Application, id=application_id, organization=organization)
    name = application.name_application
    application.delete()
    messages.success(request, f"Заявка удалена: {name}")
    return redirect("parmodels:applications_list")


@login_required
def equipment_delete_confirm(request, equipment_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "equipment.delete", request=request)
    equipment = get_object_or_404(Equipment, id=equipment_id, organization=organization)
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
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "equipment.delete", request=request)
    equipment = get_object_or_404(Equipment, id=equipment_id, organization=organization)
    name = equipment.name_equipment
    equipment.delete()
    messages.success(request, f"Оборудование удалено: {name}")
    return redirect("parmodels:equipment_list")


@login_required
def location_delete_confirm(request, location_id: int):
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "locations.delete", request=request)
    location = get_object_or_404(Location, id=location_id, organization=organization)
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
    organization = _require_current_organization(request)
    if organization is None:
        return _organization_access_denied(request)
    require_permission(request.user, "locations.delete", request=request)
    location = get_object_or_404(Location, id=location_id, organization=organization)
    name = location.name
    descendant_ids = _location_descendant_ids(location)
    ids_to_delete = descendant_ids + [location.id]

    with transaction.atomic():
        Location.objects.filter(id__in=ids_to_delete, organization=organization).delete()

    messages.success(request, f"Локация удалена: {name}")
    return redirect("parmodels:locations_list")


@login_required
def users_list(request):
    membership = get_current_membership(request.user, request=request)
    if membership is None:
        return _organization_access_denied(request)
    require_permission(request.user, "users.view", request=request)
    organization = membership.organization
    q = (request.GET.get("q") or "").strip()
    organization_id = (request.GET.get("organization") or "").strip()
    department_id = (request.GET.get("department") or "").strip()
    date_reception_from = (request.GET.get("date_reception_from") or "").strip()
    date_reception_to = (request.GET.get("date_reception_to") or "").strip()
    filter_errors = []
    date_reception_from_date = _parse_filter_date(date_reception_from)
    date_reception_to_date = _parse_filter_date(date_reception_to)
    invalid_date_reception_range = bool(
        date_reception_from
        and date_reception_to
        and date_reception_from_date
        and date_reception_to_date
        and date_reception_from_date > date_reception_to_date
    )
    if invalid_date_reception_range:
        filter_errors.append("Неверный диапазон дат")

    memberships = (
        OrganizationMembership.objects
        .filter(organization=organization, status=OrganizationMembership.Status.ACTIVE)
        .select_related("user", "organization", "department")
        .order_by("user__last_name", "user__first_name", "user__email")
    )

    if q:
        memberships = memberships.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(user__username__icontains=q)
        )

    if organization_id and organization_id != str(organization.id):
        memberships = memberships.none()
    if department_id:
        memberships = memberships.filter(department_id=department_id)
    if not invalid_date_reception_range:
        if date_reception_from_date:
            memberships = memberships.filter(date_reception__gte=date_reception_from_date)
        if date_reception_to_date:
            memberships = memberships.filter(date_reception__lte=date_reception_to_date)

    departments = Department.objects.filter(organization=organization).order_by("name")

    return render(
        request,
        "users_list.html",
        {
            "memberships": memberships,
            "q": q,
            "organizations": [organization],
            "departments": departments,
            "current_organization": organization,
            "filter_errors": filter_errors,
            **permission_flags(request.user, request=request),
            "filters": {
                "organization": organization_id,
                "department": department_id,
                "date_reception_from": date_reception_from,
                "date_reception_to": date_reception_to,
            },
        },
    )


@login_required
def organization_invitation_create(request):
    membership = get_current_membership(request.user, request=request)
    if membership is None:
        return _organization_access_denied(request)
    require_permission(request.user, "users.invite", request=request)

    organization = membership.organization
    if request.method == "POST":
        form = OrganizationInvitationForm(request.POST, organization=organization)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.organization = organization
            invitation.invited_by = request.user
            invitation.status = OrganizationInvitation.Status.PENDING
            invitation.expires_at = timezone.now() + timedelta(days=7)
            invitation.save()
            invite_url = request.build_absolute_uri(
                reverse("parmodels:organization_invitation_accept", args=[invitation.token])
            )
            return render(
                request,
                "organization_invitation_done.html",
                {"invitation": invitation, "invite_url": invite_url},
            )
    else:
        form = OrganizationInvitationForm(organization=organization)

    return render(
        request,
        "organization_invitation_form.html",
        {"form": form, "organization": organization},
    )


def _activate_invitation_membership(invitation, user):
    membership, _ = OrganizationMembership.objects.update_or_create(
        organization=invitation.organization,
        user=user,
        defaults={
            "role": invitation.role,
            "status": OrganizationMembership.Status.ACTIVE,
            "department": invitation.department,
            "position": invitation.position,
            "date_reception": invitation.date_reception,
            "invited_by": invitation.invited_by,
            "joined_at": timezone.now(),
        },
    )
    invitation.status = OrganizationInvitation.Status.ACCEPTED
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["status", "accepted_at"])
    return membership


def organization_invitation_accept(request, token):
    invitation = get_object_or_404(
        OrganizationInvitation.objects.select_related("organization", "department", "invited_by"),
        token=token,
    )

    if invitation.status != OrganizationInvitation.Status.PENDING:
        return render(
            request,
            "organization_invitation_invalid.html",
            {"invitation": invitation, "reason": "Приглашение уже использовано или отменено."},
            status=400,
        )

    if invitation.expires_at < timezone.now():
        invitation.status = OrganizationInvitation.Status.EXPIRED
        invitation.save(update_fields=["status"])
        return render(
            request,
            "organization_invitation_invalid.html",
            {"invitation": invitation, "reason": "Срок действия приглашения истек."},
            status=400,
        )

    User = get_user_model()
    existing_user = User.objects.filter(email__iexact=invitation.email).first()

    if existing_user:
        if request.method == "POST":
            _activate_invitation_membership(invitation, existing_user)
            messages.success(request, "Приглашение принято. Теперь можно войти в систему.")
            return redirect("parmodels:login")
        return render(
            request,
            "organization_invitation_accept.html",
            {"invitation": invitation, "existing_user": existing_user},
        )

    if request.method == "POST":
        form = InvitationRegistrationForm(request.POST, email=invitation.email)
        if form.is_valid():
            user = form.save()
            _activate_invitation_membership(invitation, user)
            messages.success(request, "Аккаунт создан. Теперь можно войти в систему.")
            return redirect("parmodels:login")
    else:
        initial_username = invitation.email.split("@", 1)[0]
        form = InvitationRegistrationForm(email=invitation.email, initial={"username": initial_username})

    return render(
        request,
        "organization_invitation_accept.html",
        {"invitation": invitation, "form": form, "existing_user": None},
    )


@login_required
def user_detail(request, user_id: int):
    current_membership = get_current_membership(request.user, request=request)
    if current_membership is None:
        return _organization_access_denied(request)
    require_permission(request.user, "users.view", request=request)
    organization = current_membership.organization
    User = get_user_model()
    user_obj = get_object_or_404(
        User.objects,
        id=user_id,
        organization_memberships__organization=organization,
        organization_memberships__status=OrganizationMembership.Status.ACTIVE,
    )
    memberships = (
        OrganizationMembership.objects
        .filter(user=user_obj, organization=organization)
        .select_related("organization", "department")
    )
    return render(request, "user_detail.html", {"user_obj": user_obj, "memberships": memberships})


@login_required
def profile(request):
    current_membership = get_current_membership(request.user, request=request)
    if current_membership is None:
        return _organization_access_denied(request)
    require_permission(request.user, "profile.view", request=request)
    active_memberships = (
        OrganizationMembership.objects
        .filter(user=request.user, organization=current_membership.organization)
        .select_related("organization", "department")
        .order_by("organization__name", "department__name")
    )
    all_active_memberships = (
        OrganizationMembership.objects
        .filter(user=request.user, status=OrganizationMembership.Status.ACTIVE)
        .select_related("organization", "department")
        .order_by("organization__name", "department__name")
    )
    show_organization_card = current_membership.role in (
        OrganizationMembership.Role.ADMIN,
        OrganizationMembership.Role.CHIEF_ENGINEER,
    )
    return render(
        request,
        "profile.html",
        {
            "memberships": active_memberships,
            "active_memberships": all_active_memberships,
            "current_membership": current_membership,
            "show_organization_card": show_organization_card,
            **permission_flags(request.user, request=request),
        },
    )


@login_required
@require_POST
def profile_switch_organization(request):
    organization_id = request.POST.get("organization_id")
    membership = (
        OrganizationMembership.objects
        .filter(
            user=request.user,
            organization_id=organization_id,
            status=OrganizationMembership.Status.ACTIVE,
        )
        .first()
    )
    if membership is None:
        raise PermissionDenied

    request.session[CURRENT_ORGANIZATION_SESSION_KEY] = membership.organization_id
    messages.success(request, f"Текущая организация: {membership.organization.name}")
    return redirect("parmodels:profile")


@login_required
def profile_edit(request):
    current_membership = get_current_membership(request.user, request=request)
    if current_membership is None:
        return _organization_access_denied(request)
    require_permission(request.user, "profile.update", request=request)
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль обновлен")
            return redirect("parmodels:profile")
    else:
        form = UserProfileForm(instance=request.user)

    return render(
        request,
        "profile_form.html",
        {
            "form": form,
            "title": "Редактирование профиля",
            "cancel_url": "parmodels:profile",
        },
    )


@require_POST
def logout_view(request):
    logout(request)
    return redirect("parmodels:login")
