from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    ApplicationViewSet,
    EquipmentViewSet,
    LocationViewSet,
    OrganizationUserViewSet,
)

app_name = "parmodels_api"

router = DefaultRouter()
router.register("locations", LocationViewSet, basename="locations")
router.register("applications", ApplicationViewSet, basename="applications")
router.register("equipment", EquipmentViewSet, basename="equipment")
router.register("users", OrganizationUserViewSet, basename="users")

urlpatterns = [
    path("", include(router.urls)),
]

