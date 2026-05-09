import json

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import (
    Application,
    Department,
    Equipment,
    History_Equipment,
    Location,
    LocationModel,
    OrganizationInvitation,
    OrganizationMembership,
)

COMMON_LABELS = {
    "organization": "Организация",
    "name": "Название",
    "name_application": "Название заявки",
    "about": "Описание",
    "deadline": "Дедлайн",
    "date_create": "Дата создания",
    "location": "Локация",
    "location_type": "Тип локации",
    "parent": "Родительская локация",
    "equipment": "Оборудование",
    "executor": "Исполнитель",
    "priority": "Приоритет",
    "status": "Статус",
    "name_equipment": "Название оборудования",
    "inventory_number": "Инвентарный номер",
    "external_id": "Внешний идентификатор",
    "date_input": "Дата ввода в эксплуатацию",
    "type_equipment": "Тип оборудования",
    "description": "Описание",
    "address_location": "Адрес",
    "first_name": "Имя",
    "last_name": "Фамилия",
    "email": "Электронная почта",
    "role": "Роль",
    "department": "Департамент",
    "position": "Должность",
    "date_reception": "Дата выхода",
}


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["organization", "parent", "name", "location_type", "description", "address_location"]
        labels = {
            "organization": COMMON_LABELS["organization"],
            "parent": COMMON_LABELS["parent"],
            "name": COMMON_LABELS["name"],
            "location_type": COMMON_LABELS["location_type"],
            "description": COMMON_LABELS["description"],
            "address_location": COMMON_LABELS["address_location"],
        }
        widgets = {
            "organization": forms.Select(attrs={"class": "form-select"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "location_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "address_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                    "placeholder": "Начните вводить адрес",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        hide_organization = kwargs.pop("hide_organization", False)
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        if hide_organization:
            self.fields.pop("organization", None)
        if organization is not None:
            if "organization" in self.fields:
                self.fields["organization"].queryset = type(organization).objects.filter(id=organization.id)
            if "parent" in self.fields:
                self.fields["parent"].queryset = Location.objects.filter(organization=organization).order_by(
                    "location_type",
                    "name",
                )


class LocationModelForm(forms.ModelForm):
    model_json = forms.CharField(
        label="JSON техплана",
        widget=forms.Textarea(
            attrs={
                "class": "form-control font-monospace",
                "rows": 12,
                "placeholder": '{"objects": [], "metadata": {"source": "manual"}}',
            }
        ),
    )

    class Meta:
        model = LocationModel
        fields = ["name", "model_json"]
        labels = {"name": COMMON_LABELS["name"]}
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def prepare_value(self, value):
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return super().prepare_value(value)

    def clean_model_json(self):
        value = self.cleaned_data["model_json"]
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"Некорректный JSON: {exc.msg}") from exc


class ApplicationForm(forms.ModelForm):
    executor_search = forms.CharField(
        label="Исполнитель",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "list": "executor-options",
                "placeholder": "Начните вводить имя, фамилию или email",
                "autocomplete": "off",
            }
        ),
    )
    deadline = forms.DateTimeField(
        label="Дедлайн",
        required=False,
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = Application
        fields = [
            "organization",
            "location",
            "equipment",
            "name_application",
            "about",
            "deadline",
            "priority",
            "status",
        ]
        labels = {
            "organization": COMMON_LABELS["organization"],
            "location": COMMON_LABELS["location"],
            "equipment": COMMON_LABELS["equipment"],
            "name_application": COMMON_LABELS["name_application"],
            "about": COMMON_LABELS["about"],
            "deadline": COMMON_LABELS["deadline"],
            "priority": COMMON_LABELS["priority"],
            "status": COMMON_LABELS["status"],
        }
        widgets = {
            "organization": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "equipment": forms.Select(attrs={"class": "form-select"}),
            "name_application": forms.TextInput(attrs={"class": "form-control"}),
            "about": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        hide_organization = kwargs.pop("hide_organization", False)
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        if hide_organization:
            self.fields.pop("organization", None)
        if organization is not None:
            if "organization" in self.fields:
                self.fields["organization"].queryset = type(organization).objects.filter(id=organization.id)
            self.fields["location"].queryset = Location.objects.filter(organization=organization).order_by(
                "location_type",
                "name",
            )
            self.fields["equipment"].queryset = Equipment.objects.filter(organization=organization).order_by(
                "name_equipment",
            )
        self.fields["location"].required = False
        self.fields["equipment"].required = False
        self.fields["priority"].required = False
        if "status" in self.fields:
            self.fields["status"].required = False
        users_queryset = get_user_model().objects.all()
        if organization is not None:
            users_queryset = users_queryset.filter(
                organization_memberships__organization=organization,
                organization_memberships__status=OrganizationMembership.Status.ACTIVE,
            ).distinct()
        self.executor_options = [
            (self._executor_label(user), user.id)
            for user in users_queryset.order_by("last_name", "first_name", "email", "username")
        ]
        initial_executor = self.initial.get("executor") or getattr(self.instance, "executor", None)
        if initial_executor:
            if not hasattr(initial_executor, "email"):
                initial_executor = get_user_model().objects.filter(id=initial_executor).first()
            if initial_executor:
                self.fields["executor_search"].initial = self._executor_label(initial_executor)
        order = [
            "organization",
            "location",
            "equipment",
            "name_application",
            "about",
            "deadline",
            "executor_search",
            "priority",
            "status",
        ]
        self.order_fields([name for name in order if name in self.fields])

    @staticmethod
    def _executor_label(user):
        full_name = user.get_full_name().strip()
        label = full_name or user.username
        if user.email:
            label = f"{label} <{user.email}>"
        return label

    def clean_executor_search(self):
        value = (self.cleaned_data.get("executor_search") or "").strip()
        if not value:
            return None
        for label, user_id in self.executor_options:
            if label == value:
                return get_user_model().objects.get(id=user_id)
        raise ValidationError("Выберите исполнителя из списка.")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.executor = self.cleaned_data.get("executor_search")
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ApplicationEditForm(ApplicationForm):
    class Meta(ApplicationForm.Meta):
        fields = [
            "organization",
            "location",
            "equipment",
            "name_application",
            "about",
            "deadline",
            "priority",
        ]


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = [
            "organization",
            "location",
            "name_equipment",
            "about",
            "inventory_number",
            "external_id",
            "date_input",
            "status",
            "type_equipment",
        ]
        labels = {
            "organization": COMMON_LABELS["organization"],
            "location": COMMON_LABELS["location"],
            "name_equipment": COMMON_LABELS["name_equipment"],
            "about": COMMON_LABELS["about"],
            "inventory_number": COMMON_LABELS["inventory_number"],
            "external_id": COMMON_LABELS["external_id"],
            "date_input": COMMON_LABELS["date_input"],
            "status": COMMON_LABELS["status"],
            "type_equipment": COMMON_LABELS["type_equipment"],
        }
        widgets = {
            "organization": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "name_equipment": forms.TextInput(attrs={"class": "form-control"}),
            "about": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "inventory_number": forms.TextInput(attrs={"class": "form-control"}),
            "external_id": forms.TextInput(attrs={"class": "form-control"}),
            "date_input": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "type_equipment": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        hide_organization = kwargs.pop("hide_organization", False)
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)
        if hide_organization:
            self.fields.pop("organization", None)
        if organization is not None:
            if "organization" in self.fields:
                self.fields["organization"].queryset = type(organization).objects.filter(id=organization.id)
            if "location" in self.fields:
                self.fields["location"].queryset = Location.objects.filter(organization=organization).order_by(
                    "location_type",
                    "name",
                )


class EquipmentEditForm(EquipmentForm):
    class Meta(EquipmentForm.Meta):
        fields = [
            "organization",
            "location",
            "name_equipment",
            "about",
            "inventory_number",
            "external_id",
            "date_input",
            "type_equipment",
        ]


class ApplicationStatusForm(forms.Form):
    status = forms.ModelChoiceField(
        label="Новый статус",
        queryset=None,
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    comment = forms.CharField(
        label="Комментарий",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        statuses = kwargs.pop("statuses")
        super().__init__(*args, **kwargs)
        self.fields["status"].queryset = statuses


class EquipmentStatusForm(forms.Form):
    status = forms.ModelChoiceField(
        label="Новый статус",
        queryset=None,
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    application = forms.ModelChoiceField(
        label="Связанная заявка",
        queryset=None,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    maintenance_type = forms.CharField(
        label="Тип обслуживания",
        required=False,
        max_length=History_Equipment._meta.get_field("maintenance_type").max_length,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    description = forms.CharField(
        label="Описание",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    result = forms.CharField(
        label="Результат",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        statuses = kwargs.pop("statuses")
        applications = kwargs.pop("applications")
        super().__init__(*args, **kwargs)
        self.fields["status"].queryset = statuses
        self.fields["application"].queryset = applications


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": COMMON_LABELS["first_name"],
            "last_name": COMMON_LABELS["last_name"],
            "email": COMMON_LABELS["email"],
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class OrganizationInvitationForm(forms.ModelForm):
    class Meta:
        model = OrganizationInvitation
        fields = ["email", "role", "department", "position", "date_reception"]
        labels = {
            "email": COMMON_LABELS["email"],
            "role": COMMON_LABELS["role"],
            "department": COMMON_LABELS["department"],
            "position": COMMON_LABELS["position"],
            "date_reception": COMMON_LABELS["date_reception"],
        }
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "position": forms.TextInput(attrs={"class": "form-control"}),
            "date_reception": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization")
        super().__init__(*args, **kwargs)
        self.fields["department"].required = False
        self.fields["department"].queryset = Department.objects.filter(organization=self.organization).order_by("name")

    def clean_department(self):
        department = self.cleaned_data.get("department")
        if department and department.organization_id != self.organization.id:
            raise ValidationError("Департамент должен принадлежать текущей организации.")
        return department


class InvitationRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        label=COMMON_LABELS["first_name"],
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label=COMMON_LABELS["last_name"],
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name", "last_name")
        labels = {
            "username": "Логин",
            "first_name": COMMON_LABELS["first_name"],
            "last_name": COMMON_LABELS["last_name"],
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.email = kwargs.pop("email")
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.email
        if commit:
            user.save()
        return user
