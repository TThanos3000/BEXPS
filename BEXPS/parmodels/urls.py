from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = "parmodels"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("", views.building_list, name="building_list"),
    path("applications/", views.applications_list, name="applications_list"),
    path("applications/create/", views.application_create, name="application_create"),
    path("applications/<int:application_id>/", views.application_detail, name="application_detail"),
    path("applications/<int:application_id>/status/", views.application_status_update, name="application_status_update"),
    path("applications/<int:application_id>/delete/confirm/", views.application_delete_confirm, name="application_delete_confirm"),
    path("applications/<int:application_id>/delete/", views.application_delete, name="application_delete"),
    path("locations/", views.locations_list, name="locations_list"),
    path("locations/create/", views.location_create_standalone, name="location_create_standalone"),
    path("locations/<int:location_id>/", views.location_detail_standalone, name="location_detail_standalone"),
    path("locations/<int:location_id>/models/add/", views.location_model_create, name="location_model_create"),
    path("locations/<int:location_id>/delete/confirm/", views.location_delete_confirm, name="location_delete_confirm"),
    path("locations/<int:location_id>/delete/", views.location_delete, name="location_delete"),
    path("equipment/", views.equipment_list, name="equipment_list"),
    path("equipment/create/", views.equipment_create, name="equipment_create"),
    path("equipment/<int:equipment_id>/", views.equipment_detail, name="equipment_detail"),
    path("equipment/<int:equipment_id>/status/", views.equipment_status_update, name="equipment_status_update"),
    path("equipment/<int:equipment_id>/delete/confirm/", views.equipment_delete_confirm, name="equipment_delete_confirm"),
    path("equipment/<int:equipment_id>/delete/", views.equipment_delete, name="equipment_delete"),
    path("users/", views.users_list, name="users_list"),
    path("users/<int:user_id>/", views.user_detail, name="user_detail"),
    path("profile/", views.profile, name="profile"),
    path("logout/", views.logout_view, name="logout"),
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
    path(
        "buildings/<int:building_id>/locations/<int:location_id>/ifc/<int:ifc_id>/ingest/",
        views.ifc_ingest_json,
        name="ifc_ingest_json",
    ),
    path(
        "buildings/<int:building_id>/locations/<int:location_id>/equipment/",
        views.location_equipment,
        name="location_equipment",
    ),
    path(
        "buildings/<int:building_id>/locations/create/",
        views.location_create,
        name="location_create"
    ),
    path(
        "buildings/<int:building_id>/locations/<int:location_id>/edit/",
        views.location_edit,
        name="location_edit"
    ),
]
