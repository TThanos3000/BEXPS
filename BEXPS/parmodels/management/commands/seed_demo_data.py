from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from parmodels.models import (
    Application,
    ApplicationPriority,
    ApplicationStatus,
    Department,
    Equipment,
    EquipmentStatus,
    EquipmentType,
    File,
    History_Application,
    History_Equipment,
    Location,
    LocationModel,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
)


class Command(BaseCommand):
    help = "Заполняет базу реалистичными демонстрационными данными BEXPS."

    def handle(self, *args, **options):
        now = timezone.now()
        User = get_user_model()

        users_data = [
            {
                "username": "admin.demo",
                "email": "admin@bexps.local",
                "first_name": "Анна",
                "last_name": "Орлова",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "username": "dispatcher.demo",
                "email": "dispatcher@bexps.local",
                "first_name": "Мария",
                "last_name": "Соколова",
            },
            {
                "username": "engineer.demo",
                "email": "engineer@bexps.local",
                "first_name": "Илья",
                "last_name": "Петров",
            },
            {
                "username": "chief.engineer.demo",
                "email": "chief@bexps.local",
                "first_name": "Сергей",
                "last_name": "Кузнецов",
            },
        ]

        users = {}
        for data in users_data:
            defaults = data.copy()
            username = defaults.pop("username")
            user, _ = User.objects.update_or_create(username=username, defaults=defaults)
            if not user.has_usable_password():
                user.set_password("demo12345")
                user.save(update_fields=["password"])
            users[username] = user

        organization, _ = Organization.objects.update_or_create(
            name="УК Бизнес-центр Север",
            defaults={
                "legal_name": "ООО Управляющая компания Бизнес-центр Север",
                "inn": "7708123456",
                "description": "Эксплуатационная компания офисного комплекса.",
                "status": Organization.Status.ACTIVE,
                "created_by": users["admin.demo"],
            },
        )

        departments = {}
        for name, description in [
            ("Эксплуатация", "Планирование и контроль эксплуатации объекта."),
            ("Инженерная служба", "Обслуживание инженерных систем здания."),
            ("Диспетчерская", "Прием, распределение и контроль заявок."),
        ]:
            departments[name], _ = Department.objects.update_or_create(
                organization=organization,
                name=name,
                defaults={"description": description},
            )

        memberships_data = [
            ("admin.demo", OrganizationMembership.Role.ADMIN, "Эксплуатация", "Руководитель проекта"),
            ("dispatcher.demo", OrganizationMembership.Role.DISPATCHER, "Диспетчерская", "Диспетчер"),
            ("engineer.demo", OrganizationMembership.Role.ENGINEER, "Инженерная служба", "Инженер ОВиК"),
            ("chief.engineer.demo", OrganizationMembership.Role.CHIEF_ENGINEER, "Инженерная служба", "Главный инженер"),
        ]
        for username, role, department_name, position in memberships_data:
            OrganizationMembership.objects.update_or_create(
                organization=organization,
                user=users[username],
                defaults={
                    "role": role,
                    "status": OrganizationMembership.Status.ACTIVE,
                    "department": departments[department_name],
                    "position": position,
                    "date_reception": now.date() - timedelta(days=120),
                    "joined_at": now - timedelta(days=120),
                    "invited_by": users["admin.demo"],
                },
            )

        OrganizationInvitation.objects.update_or_create(
            organization=organization,
            email="new.engineer@bexps.local",
            defaults={
                "role": OrganizationMembership.Role.ENGINEER,
                "status": OrganizationInvitation.Status.PENDING,
                "invited_by": users["admin.demo"],
                "expires_at": now + timedelta(days=14),
            },
        )

        app_statuses = {
            code: ApplicationStatus.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": description, "is_active": True},
            )[0]
            for code, name, description in [
                ("new", "Новая", "Заявка создана и ожидает обработки."),
                ("in_progress", "В работе", "Заявка назначена исполнителю."),
                ("waiting_review", "Ожидает проверки", "Работы выполнены и ждут проверки."),
                ("completed", "Выполнена", "Заявка закрыта."),
                ("cancelled", "Отменена", "Заявка отменена."),
            ]
        }
        priorities = {
            code: ApplicationPriority.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": description, "weight": weight, "is_active": True},
            )[0]
            for code, name, weight, description in [
                ("low", "Низкий", 10, "Можно выполнить в плановом режиме."),
                ("medium", "Средний", 20, "Требует обработки в рабочем порядке."),
                ("high", "Высокий", 30, "Влияет на комфорт или эксплуатацию."),
                ("critical", "Критический", 40, "Требует срочного реагирования."),
            ]
        }
        equipment_statuses = {
            code: EquipmentStatus.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": description, "is_active": True},
            )[0]
            for code, name, description in [
                ("working", "Работает", "Оборудование находится в эксплуатации."),
                ("needs_service", "Требует обслуживания", "Нужно плановое или внеплановое обслуживание."),
                ("faulty", "Неисправно", "Оборудование неисправно."),
                ("decommissioned", "Выведено из эксплуатации", "Оборудование больше не используется."),
            ]
        }
        equipment_types = {
            code: EquipmentType.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": description, "is_active": True},
            )[0]
            for code, name, description in [
                ("ventilation", "Вентиляция", "Системы вентиляции и воздухообмена."),
                ("electricity", "Электрика", "Электроснабжение и электрощитовое оборудование."),
                ("plumbing", "Сантехника", "Водоснабжение и водоотведение."),
                ("fire_safety", "Пожарная безопасность", "Пожарная сигнализация и связанные системы."),
                ("climate", "Климатическое оборудование", "Кондиционирование и климат-контроль."),
            ]
        }

        building, _ = Location.objects.update_or_create(
            organization=organization,
            parent=None,
            name="Бизнес-центр Север, корпус А",
            defaults={
                "location_type": Location.LocationType.BUILDING,
                "description": "Основное офисное здание бизнес-центра.",
                "address_location": "Москва, ул. Северная, 15",
            },
        )
        floor_1, _ = Location.objects.update_or_create(
            organization=organization,
            parent=building,
            name="1 этаж",
            defaults={"location_type": Location.LocationType.FLOOR, "description": "Первый этаж с инженерными помещениями."},
        )
        floor_2, _ = Location.objects.update_or_create(
            organization=organization,
            parent=building,
            name="2 этаж",
            defaults={"location_type": Location.LocationType.FLOOR, "description": "Офисный этаж арендаторов."},
        )
        pump_room, _ = Location.objects.update_or_create(
            organization=organization,
            parent=floor_1,
            name="Насосная",
            defaults={"location_type": Location.LocationType.ROOM, "description": "Помещение насосного оборудования."},
        )
        switchboard_room, _ = Location.objects.update_or_create(
            organization=organization,
            parent=floor_1,
            name="Электрощитовая",
            defaults={"location_type": Location.LocationType.ROOM, "description": "Главный распределительный щит."},
        )
        office_room, _ = Location.objects.update_or_create(
            organization=organization,
            parent=floor_2,
            name="Офис 204",
            defaults={"location_type": Location.LocationType.ROOM, "description": "Офисное помещение арендатора."},
        )
        fire_zone, _ = Location.objects.update_or_create(
            organization=organization,
            parent=office_room,
            name="Зона датчиков ПС",
            defaults={"location_type": Location.LocationType.ZONE, "description": "Зона размещения датчиков пожарной сигнализации."},
        )

        LocationModel.objects.update_or_create(
            location=building,
            name="Демонстрационный техплан",
            defaults={"model_json": {"objects": [], "metadata": {"source": "test"}}},
        )

        equipment_data = [
            ("Вентиляционная установка ВУ-1", "VENT-001", "EXT-VENT-001", equipment_statuses["needs_service"], equipment_types["ventilation"], floor_2, "2024-03-15"),
            ("Насос повысительный Н-2", "PUMP-002", "EXT-PUMP-002", equipment_statuses["working"], equipment_types["plumbing"], pump_room, "2023-11-20"),
            ("Электрощит ГРЩ-1", "EL-101", "EXT-EL-101", equipment_statuses["working"], equipment_types["electricity"], switchboard_room, "2022-06-01"),
            ("Система пожарной сигнализации ПС-204", "FS-204", "EXT-FS-204", equipment_statuses["needs_service"], equipment_types["fire_safety"], fire_zone, "2024-01-10"),
            ("Кондиционер настенный К-204", "AC-204", "EXT-AC-204", equipment_statuses["faulty"], equipment_types["climate"], office_room, "2023-05-25"),
        ]
        equipment = {}
        for name, inventory_number, external_id, status, equipment_type, location, date_input in equipment_data:
            equipment[name], _ = Equipment.objects.update_or_create(
                organization=organization,
                inventory_number=inventory_number,
                defaults={
                    "location": location,
                    "name_equipment": name,
                    "about": f"Демонстрационная единица оборудования: {name}.",
                    "external_id": external_id,
                    "date_input": date_input,
                    "status": status,
                    "type_equipment": equipment_type,
                },
            )

        applications_data = [
            ("Проверить работу вентиляции", "Проверить приток и вытяжку на 2 этаже.", app_statuses["new"], priorities["medium"], equipment["Вентиляционная установка ВУ-1"], floor_2, users["dispatcher.demo"], users["engineer.demo"], 2),
            ("Заменить фильтры", "Заменить фильтры вентиляционной установки ВУ-1.", app_statuses["in_progress"], priorities["high"], equipment["Вентиляционная установка ВУ-1"], floor_2, users["dispatcher.demo"], users["engineer.demo"], 1),
            ("Устранить протечку", "Проверить насосную и устранить следы протечки.", app_statuses["in_progress"], priorities["critical"], equipment["Насос повысительный Н-2"], pump_room, users["dispatcher.demo"], users["chief.engineer.demo"], 0),
            ("Провести диагностику электрощита", "Проверить нагрев автоматов и состояние контактов.", app_statuses["waiting_review"], priorities["high"], equipment["Электрощит ГРЩ-1"], switchboard_room, users["admin.demo"], users["chief.engineer.demo"], 3),
            ("Проверить датчик пожарной сигнализации", "Проверить датчик в офисе 204 и журнал событий.", app_statuses["completed"], priorities["medium"], equipment["Система пожарной сигнализации ПС-204"], fire_zone, users["dispatcher.demo"], users["engineer.demo"], -1),
        ]
        applications = {}
        for name, about, status, priority, item, location, creator, executor, days in applications_data:
            applications[name], _ = Application.objects.update_or_create(
                organization=organization,
                name_application=name,
                defaults={
                    "location": location,
                    "equipment": item,
                    "about": about,
                    "date_create": now - timedelta(days=1),
                    "deadline": now + timedelta(days=days),
                    "creator": creator,
                    "executor": executor,
                    "priority": priority,
                    "status": status,
                },
            )

        demo_file_content = b"Demo service act for BEXPS seed data."
        demo_file, _ = File.objects.update_or_create(
            organization=organization,
            file_name="Акт обслуживания вентиляции.pdf",
            defaults={
                "file_path": ContentFile(
                    demo_file_content,
                    name="demo-service-act.pdf",
                ),
                "file_type": "pdf",
                "file_size": len(demo_file_content),
                "uploaded_by": users["engineer.demo"],
            },
        )

        History_Application.objects.update_or_create(
            application=applications["Заменить фильтры"],
            comment="Заявка принята в работу инженером.",
            defaults={
                "organization": organization,
                "user": users["engineer.demo"],
                "status_old": app_statuses["new"],
                "status_new": app_statuses["in_progress"],
                "file": None,
            },
        )
        History_Equipment.objects.update_or_create(
            equipment=equipment["Вентиляционная установка ВУ-1"],
            maintenance_type="Плановое обслуживание",
            defaults={
                "organization": organization,
                "application": applications["Заменить фильтры"],
                "user": users["engineer.demo"],
                "description": "Проверены фильтры и состояние ремня привода.",
                "result": "Требуется замена фильтров.",
                "file": demo_file,
                "performed_at": now - timedelta(hours=5),
            },
        )

        self.stdout.write(self.style.SUCCESS("Демонстрационные данные добавлены или обновлены."))
        self.stdout.write("Пользователи: admin.demo, dispatcher.demo, engineer.demo, chief.engineer.demo")
        self.stdout.write("Пароль для demo-пользователей без заданного пароля: demo12345")
