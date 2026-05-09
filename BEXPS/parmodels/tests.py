from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Application,
    ApplicationPriority,
    ApplicationStatus,
    Department,
    Equipment,
    EquipmentStatus,
    EquipmentType,
    History_Application,
    Location,
    LocationModel,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
)
from .permissions import can_update_application_status, has_permission
from .services import CURRENT_ORGANIZATION_SESSION_KEY


User = get_user_model()


class TestDataMixin:
    user_index = 0

    @classmethod
    def create_organization(cls, name="Test organization"):
        return Organization.objects.create(name=name, legal_name=f"{name} LLC")

    @classmethod
    def create_user(cls, username=None, email=None, password="password123", **extra):
        cls.user_index += 1
        username = username or f"user{cls.user_index}"
        email = email or f"{username}@example.com"
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            **extra,
        )
        return user

    @classmethod
    def create_department(cls, organization, name="Engineering"):
        return Department.objects.create(organization=organization, name=name)

    @classmethod
    def create_membership(
        cls,
        user,
        organization,
        role=OrganizationMembership.Role.ENGINEER,
        status=OrganizationMembership.Status.ACTIVE,
        department=None,
    ):
        return OrganizationMembership.objects.create(
            user=user,
            organization=organization,
            role=role,
            status=status,
            department=department,
            joined_at=timezone.now(),
        )

    @classmethod
    def create_user_with_role(cls, organization, role, username=None):
        user = cls.create_user(username=username or role)
        membership = cls.create_membership(user, organization, role=role)
        return user, membership

    @classmethod
    def create_location(cls, organization, name="Location", parent=None, address=""):
        return Location.objects.create(
            organization=organization,
            name=name,
            parent=parent,
            location_type=Location.LocationType.ROOM,
            address_location=address,
        )

    @classmethod
    def create_location_model(cls, location, model_json=None):
        return LocationModel.objects.create(
            location=location,
            name=f"Model {location.name}",
            model_json=model_json or {"objects": [], "metadata": {"source": "test"}},
        )

    @classmethod
    def create_equipment_status(cls, code="working", name="Работает"):
        return EquipmentStatus.objects.create(code=code, name=name)

    @classmethod
    def create_equipment_type(cls, code="ventilation", name="Вентиляция"):
        return EquipmentType.objects.create(code=code, name=name)

    @classmethod
    def create_application_status(cls, code="new", name="Новая", is_system=False):
        return ApplicationStatus.objects.create(
            code=code,
            name=name,
            is_system=is_system,
        )

    @classmethod
    def create_application_priority(cls, code="medium", name="Средний", weight=30):
        return ApplicationPriority.objects.create(code=code, name=name, weight=weight)

    @classmethod
    def create_equipment(
        cls,
        organization,
        location=None,
        name="Equipment",
        status=None,
        type_equipment=None,
        external_id="",
    ):
        return Equipment.objects.create(
            organization=organization,
            location=location,
            name_equipment=name,
            status=status,
            type_equipment=type_equipment,
            inventory_number=f"INV-{name}",
            external_id=external_id,
        )

    @classmethod
    def create_application(
        cls,
        organization,
        name="Application",
        location=None,
        equipment=None,
        creator=None,
        executor=None,
        status=None,
        priority=None,
        deadline=None,
    ):
        return Application.objects.create(
            organization=organization,
            location=location,
            equipment=equipment,
            creator=creator,
            executor=executor,
            status=status,
            priority=priority,
            name_application=name,
            about="Test application",
            date_create=timezone.now(),
            deadline=deadline,
        )

    @classmethod
    def create_invitation(
        cls,
        organization,
        email="invitee@example.com",
        role=OrganizationMembership.Role.ENGINEER,
        status=OrganizationInvitation.Status.PENDING,
        invited_by=None,
        expires_at=None,
    ):
        return OrganizationInvitation.objects.create(
            organization=organization,
            email=email,
            role=role,
            status=status,
            invited_by=invited_by,
            expires_at=expires_at or (timezone.now() + timezone.timedelta(days=7)),
        )


class BaseParmodelsTestCase(TestDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = cls.create_organization("BEXPS Org")
        cls.other_organization = cls.create_organization("Other Org")
        cls.department = cls.create_department(cls.organization, "Engineering")

        cls.admin, cls.admin_membership = cls.create_user_with_role(
            cls.organization,
            OrganizationMembership.Role.ADMIN,
            "admin",
        )
        cls.dispatcher, cls.dispatcher_membership = cls.create_user_with_role(
            cls.organization,
            OrganizationMembership.Role.DISPATCHER,
            "dispatcher",
        )
        cls.engineer, cls.engineer_membership = cls.create_user_with_role(
            cls.organization,
            OrganizationMembership.Role.ENGINEER,
            "engineer",
        )
        cls.chief_engineer, cls.chief_membership = cls.create_user_with_role(
            cls.organization,
            OrganizationMembership.Role.CHIEF_ENGINEER,
            "chief",
        )

        cls.other_user = cls.create_user("other")
        cls.create_membership(
            cls.other_user,
            cls.other_organization,
            role=OrganizationMembership.Role.ADMIN,
        )

        cls.location = cls.create_location(cls.organization, "Main room")
        cls.other_location = cls.create_location(cls.other_organization, "Other room")
        cls.equipment_status = cls.create_equipment_status()
        cls.equipment_type = cls.create_equipment_type()
        cls.equipment = cls.create_equipment(
            cls.organization,
            location=cls.location,
            status=cls.equipment_status,
            type_equipment=cls.equipment_type,
            name="Pump",
        )
        cls.other_equipment = cls.create_equipment(
            cls.other_organization,
            location=cls.other_location,
            name="Other pump",
        )
        cls.new_status = cls.create_application_status("new", "Новая")
        cls.in_progress_status = cls.create_application_status("in_progress", "В работе")
        cls.completed_status = ApplicationStatus.objects.update_or_create(
            code="completed",
            defaults={
                "name": "Выполнено",
                "is_system": True,
                "color_code": "#198754",
            },
        )[0]
        cls.priority = cls.create_application_priority("high", "Высокий", weight=80)
        cls.application = cls.create_application(
            cls.organization,
            location=cls.location,
            equipment=cls.equipment,
            creator=cls.dispatcher,
            executor=cls.engineer,
            status=cls.new_status,
            priority=cls.priority,
            name="Check pump",
        )
        cls.other_application = cls.create_application(
            cls.other_organization,
            location=cls.other_location,
            equipment=cls.other_equipment,
            creator=cls.other_user,
            executor=cls.other_user,
            status=cls.new_status,
            priority=cls.priority,
            name="Other application",
        )

    def setUp(self):
        cache.clear()

    def login(self, user=None):
        self.client.force_login(user or self.admin)


class AuthOrganizationTests(BaseParmodelsTestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("parmodels:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("parmodels:login"), response["Location"])

    def test_authenticated_user_can_open_dashboard(self):
        self.login(self.admin)
        response = self.client.get(reverse("parmodels:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_user_sees_only_current_organization_locations(self):
        self.login(self.admin)
        response = self.client.get(reverse("parmodels:locations_list"))
        locations = [row["location"] for row in response.context["location_nodes"]]
        self.assertIn(self.location, locations)
        self.assertNotIn(self.other_location, locations)

    def test_direct_access_to_other_organization_object_returns_404(self):
        self.login(self.admin)
        response = self.client.get(
            reverse("parmodels:location_detail_standalone", args=[self.other_location.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_switch_organization_requires_active_membership(self):
        self.login(self.admin)
        response = self.client.post(
            reverse("parmodels:profile_switch_organization"),
            {"organization_id": self.other_organization.id},
        )
        self.assertEqual(response.status_code, 403)

        self.create_membership(
            self.admin,
            self.other_organization,
            role=OrganizationMembership.Role.ADMIN,
        )
        response = self.client.post(
            reverse("parmodels:profile_switch_organization"),
            {"organization_id": self.other_organization.id},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.session[CURRENT_ORGANIZATION_SESSION_KEY],
            self.other_organization.id,
        )


class RolePermissionTests(BaseParmodelsTestCase):
    def test_role_matrix_core_permissions(self):
        self.assertTrue(has_permission(self.admin, "equipment.delete"))
        self.assertTrue(has_permission(self.dispatcher, "applications.create"))
        self.assertFalse(has_permission(self.engineer, "equipment.delete"))
        self.assertTrue(has_permission(self.chief_engineer, "locations.update"))

    def test_engineer_can_update_only_own_application_status(self):
        own_application = self.application
        foreign_application = self.create_application(
            self.organization,
            executor=self.dispatcher,
            status=self.new_status,
            priority=self.priority,
            name="Foreign task",
        )
        self.assertTrue(can_update_application_status(self.engineer, own_application))
        self.assertFalse(can_update_application_status(self.engineer, foreign_application))

    def test_engineer_delete_equipment_returns_403(self):
        self.login(self.engineer)
        response = self.client.post(reverse("parmodels:equipment_delete", args=[self.equipment.id]))
        self.assertEqual(response.status_code, 403)

    def test_engineer_cannot_update_foreign_application_status_via_view(self):
        foreign_application = self.create_application(
            self.organization,
            executor=self.dispatcher,
            status=self.new_status,
            priority=self.priority,
        )
        self.login(self.engineer)
        response = self.client.post(
            reverse("parmodels:application_status_update", args=[foreign_application.id]),
            {"status": self.in_progress_status.id, "comment": "try"},
        )
        self.assertEqual(response.status_code, 403)

    def test_chief_engineer_can_open_location_create_and_edit(self):
        self.login(self.chief_engineer)
        create_response = self.client.get(reverse("parmodels:location_create_standalone"))
        edit_response = self.client.get(
            reverse("parmodels:location_edit_standalone", args=[self.location.id])
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(edit_response.status_code, 200)

    def test_non_admin_cannot_invite_users(self):
        self.login(self.engineer)
        response = self.client.get(reverse("parmodels:organization_invitation_create"))
        self.assertEqual(response.status_code, 403)


class LocationTests(BaseParmodelsTestCase):
    @patch("parmodels.views.geocode_yandex_address", return_value=None)
    def test_location_with_address_saves_when_geocoding_fails(self, geocode):
        self.login(self.admin)
        response = self.client.post(
            reverse("parmodels:location_create_standalone"),
            {
                "parent": "",
                "name": "Addressed room",
                "location_type": Location.LocationType.ROOM,
                "description": "",
                "address_location": "Moscow, Test street",
            },
        )
        self.assertEqual(response.status_code, 302)
        location = Location.objects.get(name="Addressed room")
        self.assertIsNone(location.latitude)
        self.assertIsNone(location.longitude)
        geocode.assert_called_once()

    @patch("parmodels.views.geocode_yandex_address")
    def test_successful_geocoding_saves_coordinates(self, geocode):
        geocode.return_value = ("55.755864", "37.617698")
        self.login(self.admin)
        self.client.post(
            reverse("parmodels:location_create_standalone"),
            {
                "parent": "",
                "name": "Geocoded room",
                "location_type": Location.LocationType.ROOM,
                "description": "",
                "address_location": "Москва, Красная площадь",
            },
        )
        location = Location.objects.get(name="Geocoded room")
        self.assertEqual(str(location.latitude), "55.755864")
        self.assertEqual(str(location.longitude), "37.617698")

    def test_parent_location_hierarchy(self):
        child = self.create_location(self.organization, "Child", parent=self.location)
        self.assertEqual(child.parent, self.location)

    def test_location_model_stores_json_and_delete_does_not_delete_location(self):
        location_model = self.create_location_model(self.location, {"objects": [{"id": 1}]})
        location_model.delete()
        self.assertTrue(Location.objects.filter(id=self.location.id).exists())
        self.assertFalse(LocationModel.objects.filter(id=location_model.id).exists())

    def test_equipment_presence_filter(self):
        empty_location = self.create_location(self.organization, "Empty room")
        self.login(self.admin)
        has_response = self.client.get(
            reverse("parmodels:locations_list"),
            {"equipment_presence": "has_equipment"},
        )
        has_locations = [row["location"] for row in has_response.context["location_nodes"]]
        self.assertIn(self.location, has_locations)
        self.assertNotIn(empty_location, has_locations)

        no_response = self.client.get(
            reverse("parmodels:locations_list"),
            {"equipment_presence": "no_equipment"},
        )
        no_locations = [row["location"] for row in no_response.context["location_nodes"]]
        self.assertIn(empty_location, no_locations)


class EquipmentTests(BaseParmodelsTestCase):
    def test_create_edit_delete_equipment(self):
        self.login(self.admin)
        create_response = self.client.post(
            reverse("parmodels:equipment_create"),
            {
                "location": self.location.id,
                "name_equipment": "Fan",
                "about": "Ventilation fan",
                "inventory_number": "FAN-1",
                "external_id": "fan-1",
                "date_input": "2026-05-01",
                "status": self.equipment_status.id,
                "type_equipment": self.equipment_type.id,
            },
        )
        self.assertEqual(create_response.status_code, 302)
        equipment = Equipment.objects.get(name_equipment="Fan")

        edit_response = self.client.post(
            reverse("parmodels:equipment_edit", args=[equipment.id]),
            {
                "location": self.location.id,
                "name_equipment": "Fan updated",
                "about": "Updated",
                "inventory_number": "FAN-1",
                "external_id": "fan-1",
                "date_input": "2026-05-01",
                "type_equipment": self.equipment_type.id,
            },
        )
        self.assertEqual(edit_response.status_code, 302)
        equipment.refresh_from_db()
        self.assertEqual(equipment.name_equipment, "Fan updated")

        delete_response = self.client.post(reverse("parmodels:equipment_delete", args=[equipment.id]))
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Equipment.objects.filter(id=equipment.id).exists())

    def test_bulk_delete_deletes_only_current_organization_equipment(self):
        self.login(self.admin)
        own_equipment = self.create_equipment(self.organization, name="Own bulk")
        other_equipment = self.other_equipment
        response = self.client.post(
            reverse("parmodels:equipment_bulk_delete"),
            {
                "equipment_ids": [str(own_equipment.id), str(other_equipment.id)],
                "redirect_query": "q=pump&page=1&per_page=25",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("q=pump", response["Location"])
        self.assertFalse(Equipment.objects.filter(id=own_equipment.id).exists())
        self.assertTrue(Equipment.objects.filter(id=other_equipment.id).exists())

    def test_bulk_delete_without_permission_returns_403(self):
        self.login(self.engineer)
        response = self.client.post(
            reverse("parmodels:equipment_bulk_delete"),
            {"equipment_ids": [str(self.equipment.id)]},
        )
        self.assertEqual(response.status_code, 403)

    def test_equipment_pagination_and_per_page_fallback(self):
        for index in range(15):
            self.create_equipment(self.organization, name=f"Paged {index}")
        self.login(self.admin)
        response = self.client.get(reverse("parmodels:equipment_list"), {"per_page": "10", "page": "2"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["per_page"], 10)
        self.assertEqual(response.context["page_obj"].number, 2)

        fallback_response = self.client.get(reverse("parmodels:equipment_list"), {"per_page": "999"})
        self.assertEqual(fallback_response.context["per_page"], 10)


class ApplicationTests(BaseParmodelsTestCase):
    def test_create_application_creates_history(self):
        self.login(self.dispatcher)
        response = self.client.post(
            reverse("parmodels:application_create"),
            {
                "location": self.location.id,
                "equipment": self.equipment.id,
                "name_application": "New application",
                "about": "Need work",
                "deadline": "2026-05-20T10:00",
                "executor_search": f"{self.engineer.username} <{self.engineer.email}>",
                "priority": self.priority.id,
                "status": self.new_status.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        application = Application.objects.get(name_application="New application")
        self.assertTrue(
            History_Application.objects.filter(
                application=application,
                comment="Заявка создана",
            ).exists()
        )

    def test_edit_application_creates_history(self):
        self.login(self.dispatcher)
        response = self.client.post(
            reverse("parmodels:application_edit", args=[self.application.id]),
            {
                "location": self.location.id,
                "equipment": self.equipment.id,
                "name_application": "Updated application",
                "about": "Updated",
                "deadline": "2026-05-20T10:00",
                "executor_search": f"{self.engineer.username} <{self.engineer.email}>",
                "priority": self.priority.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            History_Application.objects.filter(
                application=self.application,
                comment="Были внесены изменения",
            ).exists()
        )

    def test_status_update_creates_history(self):
        self.login(self.engineer)
        response = self.client.post(
            reverse("parmodels:application_status_update", args=[self.application.id]),
            {"status": self.in_progress_status.id, "comment": "Started"},
        )
        self.assertEqual(response.status_code, 302)
        history = History_Application.objects.get(
            application=self.application,
            comment="Started",
        )
        self.assertEqual(history.status_old, self.new_status)
        self.assertEqual(history.status_new, self.in_progress_status)

    def test_mine_filter_returns_only_user_applications(self):
        self.login(self.engineer)
        response = self.client.get(reverse("parmodels:applications_list"), {"mine": "1"})
        self.assertIn(self.application, response.context["applications"])
        self.assertNotIn(self.other_application, response.context["applications"])

    def test_invalid_deadline_range_sets_filter_error(self):
        self.login(self.admin)
        response = self.client.get(
            reverse("parmodels:applications_list"),
            {"deadline_from": "2026-05-20", "deadline_to": "2026-05-01"},
        )
        self.assertIn("Неверный диапазон дат", response.context["filter_errors"])

    def test_completed_applications_are_separated(self):
        completed_application = self.create_application(
            self.organization,
            executor=self.engineer,
            status=self.completed_status,
            priority=self.priority,
            name="Completed task",
        )
        self.login(self.admin)
        response = self.client.get(reverse("parmodels:applications_list"))
        self.assertIn(completed_application, response.context["completed_applications"])
        self.assertNotIn(completed_application, response.context["applications"])


class ReferenceAndWorkloadTests(BaseParmodelsTestCase):
    def test_completed_status_exists_and_is_protected(self):
        status = ApplicationStatus.objects.get(code="completed")
        self.assertTrue(status.is_system)
        with self.assertRaises(ValidationError):
            status.delete()

    def test_priority_weight_is_used_for_user_workload(self):
        self.login(self.admin)
        response = self.client.get(reverse("parmodels:users_list"))
        engineer_membership = next(
            item for item in response.context["memberships"] if item.user_id == self.engineer.id
        )
        self.assertEqual(engineer_membership.workload_value, self.priority.weight)

    def test_priority_weight_is_used_for_team_load(self):
        self.login(self.admin)
        response = self.client.get(reverse("parmodels:dashboard"))
        self.assertEqual(response.context["team_load"], self.priority.weight)


class InvitationTests(BaseParmodelsTestCase):
    @patch("parmodels.views.send_organization_invitation_email", return_value=1)
    def test_admin_can_create_invitation_and_email_is_called(self, send_email):
        self.login(self.admin)
        response = self.client.post(
            reverse("parmodels:organization_invitation_create"),
            {
                "email": "new.engineer@example.com",
                "role": OrganizationMembership.Role.ENGINEER,
                "department": self.department.id,
                "position": "Engineer",
                "date_reception": "2026-05-10",
            },
        )
        self.assertEqual(response.status_code, 200)
        invitation = OrganizationInvitation.objects.get(email="new.engineer@example.com")
        self.assertEqual(invitation.organization, self.organization)
        send_email.assert_called_once()

    @patch("parmodels.views.logger.exception")
    @patch("parmodels.views.send_organization_invitation_email", side_effect=RuntimeError("SMTP down"))
    def test_invitation_is_created_when_email_fails(self, send_email, log_exception):
        self.login(self.admin)
        response = self.client.post(
            reverse("parmodels:organization_invitation_create"),
            {
                "email": "mail.failed@example.com",
                "role": OrganizationMembership.Role.ENGINEER,
                "department": "",
                "position": "",
                "date_reception": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(OrganizationInvitation.objects.filter(email="mail.failed@example.com").exists())
        send_email.assert_called_once()
        log_exception.assert_called_once()

    def test_non_admin_cannot_create_invitation(self):
        self.login(self.dispatcher)
        response = self.client.post(
            reverse("parmodels:organization_invitation_create"),
            {"email": "blocked@example.com", "role": OrganizationMembership.Role.ENGINEER},
        )
        self.assertEqual(response.status_code, 403)

    def test_accept_invitation_creates_membership(self):
        existing_user = self.create_user("invitee", email="invitee@example.com")
        invitation = self.create_invitation(
            self.organization,
            email=existing_user.email,
            invited_by=self.admin,
        )
        response = self.client.post(
            reverse("parmodels:organization_invitation_accept", args=[invitation.token])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            OrganizationMembership.objects.filter(
                organization=self.organization,
                user=existing_user,
                status=OrganizationMembership.Status.ACTIVE,
            ).exists()
        )
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, OrganizationInvitation.Status.ACCEPTED)

    def test_accepted_invitation_cannot_be_reused(self):
        invitation = self.create_invitation(
            self.organization,
            status=OrganizationInvitation.Status.ACCEPTED,
        )
        response = self.client.get(
            reverse("parmodels:organization_invitation_accept", args=[invitation.token])
        )
        self.assertEqual(response.status_code, 400)

    def test_expired_invitation_cannot_be_accepted(self):
        invitation = self.create_invitation(
            self.organization,
            email="expired@example.com",
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        response = self.client.get(
            reverse("parmodels:organization_invitation_accept", args=[invitation.token])
        )
        invitation.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(invitation.status, OrganizationInvitation.Status.EXPIRED)


class ValidationTests(BaseParmodelsTestCase):
    def test_membership_department_must_belong_to_same_organization(self):
        user = self.create_user("department-check")
        foreign_department = self.create_department(self.other_organization, "Foreign")
        with self.assertRaises(ValidationError):
            self.create_membership(
                user,
                self.organization,
                role=OrganizationMembership.Role.DISPATCHER,
                department=foreign_department,
            )
