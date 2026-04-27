from django import forms
from .models import IfcModel, Location


class IfcModelUploadForm(forms.ModelForm):
    class Meta:
        model = IfcModel
        fields = ["model_name", "ifc_file"]
        widgets = {
            "model_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Например: 1 этаж, АР, версия 1"}),
            "ifc_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_ifc_file(self):
        f = self.cleaned_data["ifc_file"]
        if not f.name.lower().endswith(".ifc"):
            raise forms.ValidationError("Нужен файл с расширением .ifc")
        return f


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["name", "parent"]  # parent можно убрать, если не используешь иерархию
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "parent": forms.Select(attrs={"class": "form-select"}),
        }
