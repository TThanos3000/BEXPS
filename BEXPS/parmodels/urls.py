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
    path("", views.dashboard, name="dashboard"),
    path("applications/", views.applications_list, name="applications_list"),
    path("applications/create/", views.application_create, name="application_create"),
    path("applications/<int:application_id>/", views.application_detail, name="application_detail"),
    path("applications/<int:application_id>/edit/", views.application_edit, name="application_edit"),
    path("applications/<int:application_id>/status/", views.application_status_update, name="application_status_update"),
    path("applications/<int:application_id>/delete/confirm/", views.application_delete_confirm, name="application_delete_confirm"),
    path("applications/<int:application_id>/delete/", views.application_delete, name="application_delete"),
    path("locations/", views.locations_list, name="locations_list"),
    path("locations/create/", views.location_create_standalone, name="location_create_standalone"),
    path("locations/<int:location_id>/", views.location_detail_standalone, name="location_detail_standalone"),
    path("locations/<int:location_id>/edit/", views.location_edit_standalone, name="location_edit_standalone"),
    path("locations/<int:location_id>/models/add/", views.location_model_create, name="location_model_create"),
    path("locations/<int:location_id>/delete/confirm/", views.location_delete_confirm, name="location_delete_confirm"),
    path("locations/<int:location_id>/delete/", views.location_delete, name="location_delete"),
    path("equipment/", views.equipment_list, name="equipment_list"),
    path("equipment/create/", views.equipment_create, name="equipment_create"),
    path("equipment/<int:equipment_id>/", views.equipment_detail, name="equipment_detail"),
    path("equipment/<int:equipment_id>/edit/", views.equipment_edit, name="equipment_edit"),
    path("equipment/<int:equipment_id>/status/", views.equipment_status_update, name="equipment_status_update"),
    path("equipment/<int:equipment_id>/delete/confirm/", views.equipment_delete_confirm, name="equipment_delete_confirm"),
    path("equipment/<int:equipment_id>/delete/", views.equipment_delete, name="equipment_delete"),
    path("users/", views.users_list, name="users_list"),
    path("users/invite/", views.organization_invitation_create, name="organization_invitation_create"),
    path("users/<int:user_id>/", views.user_detail, name="user_detail"),
    path("invitations/<uuid:token>/", views.organization_invitation_accept, name="organization_invitation_accept"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("profile/switch-organization/", views.profile_switch_organization, name="profile_switch_organization"),
    path("logout/", views.logout_view, name="logout"),
]
