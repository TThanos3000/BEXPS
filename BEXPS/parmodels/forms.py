import json

from django import forms
from django.contrib.auth import get_user_model

from .models import (
    Application,
    Equipment,
    File,
    History_Equipment,
    Location,
    LocationModel,
)


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ["file_name", "file_path"]
        widgets = {
            "file_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Например: 1 этаж, АР, версия 1"}),
            "file_path": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_file_path(self):
        f = self.cleaned_data["file_path"]
        if not f.name.lower().endswith(".ifc"):
            raise forms.ValidationError("Нужен файл с расширением .ifc")
        return f


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["organization", "parent", "name", "location_type", "description", "address_location"]
        widgets = {
            "organization": forms.Select(attrs={"class": "form-select"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "location_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "address_location": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


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
    deadline = forms.DateTimeField(
        label="Дедлайн",
        required=False,
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
        widget=forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
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
            "executor",
            "priority",
            "status",
        ]
        widgets = {
            "organization": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "equipment": forms.Select(attrs={"class": "form-select"}),
            "name_application": forms.TextInput(attrs={"class": "form-control"}),
            "about": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "executor": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].required = False
        self.fields["equipment"].required = False
        self.fields["executor"].required = False
        self.fields["priority"].required = False
        self.fields["status"].required = False
        self.fields["executor"].queryset = get_user_model().objects.order_by("last_name", "first_name", "username")


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
        widgets = {
            "organization": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "name_equipment": forms.TextInput(attrs={"class": "form-control"}),
            "about": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "inventory_number": forms.TextInput(attrs={"class": "form-control"}),
            "external_id": forms.TextInput(attrs={"class": "form-control"}),
            "date_input": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "type_equipment": forms.Select(attrs={"class": "form-select"}),
        }


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
