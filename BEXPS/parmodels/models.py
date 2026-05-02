import uuid

from django.conf import settings
from django.db import models


class Location(models.Model):
    class LocationType(models.TextChoices):
        BUILDING = "building", "Building"
        FLOOR = "floor", "Floor"
        ROOM = "room", "Room"
        ZONE = "zone", "Zone"

    organization = models.ForeignKey(
        "Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locations",
    )
    name = models.CharField(max_length=255)
    location_type = models.CharField(
        max_length=16,
        choices=LocationType.choices,
        default=LocationType.ROOM,
    )
    description = models.TextField(blank=True)
    address_location = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self) -> str:
        if self.parent:
            return f"{self.parent.name} / {self.name}"
        return self.name


class Organization(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        BLOCKED = "blocked", "Blocked"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    inn = models.CharField(max_length=32, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Department(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="departments",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uq_department_organization_name",
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization.name} / {self.name}"


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        DISPATCHER = "dispatcher", "Dispatcher"
        ENGINEER = "engineer", "Engineer"
        CHIEF_ENGINEER = "chief_engineer", "Chief engineer"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INVITED = "invited", "Invited"
        BLOCKED = "blocked", "Blocked"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.ENGINEER,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    position = models.CharField(max_length=255, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
    )
    date_reception = models.DateField(null=True, blank=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_membership_invitations",
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="uq_membership_organization_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} / {self.organization} / {self.role}"


class OrganizationInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=32,
        choices=OrganizationMembership.Role.choices,
        default=OrganizationMembership.Role.ENGINEER,
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_organization_invitations",
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.email} / {self.organization} / {self.status}"


class LocationModel(models.Model):
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="location_models",
    )
    name = models.CharField(max_length=255)
    model_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.location} / {self.name}"


class EquipmentStatus(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class EquipmentType(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class ApplicationStatus(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class ApplicationPriority(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    weight = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Equipment(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment",
    )
    name_equipment = models.CharField(max_length=255)
    about = models.TextField(blank=True)
    inventory_number = models.CharField(max_length=128, blank=True)
    external_id = models.CharField(max_length=128, blank=True)
    date_input = models.DateField(null=True, blank=True)
    status = models.ForeignKey(
        EquipmentStatus,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="equipment",
    )
    type_equipment = models.ForeignKey(
        EquipmentType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="equipment",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name_equipment


class Application(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    name_application = models.CharField(max_length=255)
    date_create = models.DateTimeField(null=True, blank=True)
    about = models.TextField(blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_applications",
    )
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_applications",
    )
    priority = models.ForeignKey(
        ApplicationPriority,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="applications",
    )
    status = models.ForeignKey(
        ApplicationStatus,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="applications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name_application


class File(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="files",
    )
    file_name = models.CharField(max_length=255)
    file_path = models.FileField(upload_to="files/")
    file_type = models.CharField(max_length=128, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_files",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.file_name


class History_Application(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application_history",
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="history",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application_history_entries",
    )
    status_old = models.ForeignKey(
        ApplicationStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="old_application_history_entries",
    )
    status_new = models.ForeignKey(
        ApplicationStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_application_history_entries",
    )
    comment = models.TextField(blank=True)
    file = models.ForeignKey(
        File,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application_history_entries",
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "History application"
        verbose_name_plural = "History applications"

    def __str__(self) -> str:
        return f"{self.application} / {self.changed_at}"


class History_Equipment(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment_history",
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="history",
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment_history",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment_history_entries",
    )
    maintenance_type = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    result = models.TextField(blank=True)
    file = models.ForeignKey(
        File,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment_history_entries",
    )
    performed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "History equipment"
        verbose_name_plural = "History equipment"

    def __str__(self) -> str:
        return f"{self.equipment} / {self.performed_at}"

