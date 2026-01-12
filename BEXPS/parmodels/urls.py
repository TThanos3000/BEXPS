from django.urls import path
from . import views

app_name = "parmodels"

urlpatterns = [
    path("", views.building_list, name="building_list"),
    path("buildings/<int:building_id>/", views.building_detail, name="building_detail"),

    path(
        "buildings/<int:building_id>/locations/<int:location_id>/",
        views.location_detail,
        name="location_detail",
    ),
    path(
        "buildings/<int:building_id>/locations/<int:location_id>/upload-ifc/",
        views.ifc_model_upload,
        name="ifc_model_upload",
    ),
    path(
        "buildings/<int:building_id>/locations/<int:location_id>/ifc/<int:ifc_model_id>/delete/",
        views.ifc_model_delete,
        name="ifc_model_delete",
    ),
]
