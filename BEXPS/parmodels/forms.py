from django import forms
from .models import File, Location


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
        fields = ["name", "location_type", "description", "address_location", "parent"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "location_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "address_location": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "parent": forms.Select(attrs={"class": "form-select"}),
        }
