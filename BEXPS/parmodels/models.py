from django.db import models


class Building(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Location(models.Model):
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    name = models.CharField(max_length=255)
    location_type = models.CharField(max_length=64)  # например: floor, room, zone
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    def __str__(self) -> str:
        return f"{self.building.name} / {self.name}"


class User(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=32)

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class IfcModel(models.Model):
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="ifc_models",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="ifc_models",
    )
    model_name = models.CharField(max_length=255)
    ifc_file = models.FileField(
        upload_to="ifc/",
        null=True,
        blank=True,
    )  # или FileField, если будешь хранить файл через Django
    ifc_sha256 = models.CharField(max_length=64, unique=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, default="uploaded")  # uploaded/parsed/error
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user",
        null=True,
    )

    def __str__(self) -> str:
        return self.model_name


class ElementType(models.Model):
    code = models.CharField(max_length=64, unique=True)  # IFCWALL, IFCDOOR ...
    ru_name = models.CharField(max_length=128)

    def __str__(self) -> str:
        return self.ru_name


class ModelElement(models.Model):
    ifc_model = models.ForeignKey(
        IfcModel,
        on_delete=models.CASCADE,
        related_name="elements",
    )
    element_type = models.ForeignKey(
        ElementType,
        on_delete=models.PROTECT,
        related_name="elements",
    )
    ifc_id = models.IntegerField(null=True, blank=True)
    global_id = models.CharField(max_length=64)
    name = models.CharField(max_length=255, blank=True)

    # Для PostgreSQL будет JSONB, для других баз просто JSON
    raw = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ifc_model", "global_id"],
                name="uq_model_elements_model_global",
            )
        ]

    def __str__(self) -> str:
        return f"{self.element_type.code} {self.global_id}"
