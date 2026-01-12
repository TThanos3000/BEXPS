from django.urls import path
from . import views

app_name = "parmodels"

urlpatterns = [
    path("", views.building_list, name="building_list"),
    path("buildings/<int:building_id>/", views.building_detail, name="building_detail"),
]
