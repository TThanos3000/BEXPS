# Текущая задача

## Цель
Добавить в проект базовый слой API на Django REST Framework для будущих интеграций и масштабирования.

API сейчас не используется текущим frontend на Django Templates, но должен быть реализован для основных сущностей:
- локации;
- заявки;
- оборудование;
- пользователи.

Также нужно добавить Swagger/OpenAPI-документацию для созданных API-ручек.

## 1. Общие требования к API

Нужно реализовать REST API для следующих сущностей:
- Location;
- Application;
- Equipment;
- User / OrganizationMembership.

API должен:
- использовать Django REST Framework;
- работать в рамках текущей session-based authentication;
- не добавлять JWT;
- проверять авторизацию пользователя;
- фильтровать данные по текущей organization пользователя;
- не отдавать данные других организаций;
- использовать существующую ролевую модель доступа;
- не ломать текущие Django Templates;
- не заменять текущие views;
- существовать параллельно с текущим серверным интерфейсом.

## 2. API локаций

Нужно добавить ручки для Location:

- GET /api/locations/
- POST /api/locations/
- GET /api/locations/{id}/
- PATCH /api/locations/{id}/
- DELETE /api/locations/{id}/

Данные:
- id;
- name;
- location_type;
- address_location;
- description;
- parent;
- organization;
- latitude;
- longitude;
- equipment_count, если возможно.

Требования:
- список локаций ограничивать текущей organization;
- при создании organization подставлять автоматически из текущей organization пользователя;
- parent должен быть только из текущей organization;
- нельзя получить или изменить локацию другой organization.

## 3. API заявок

Нужно добавить ручки для Application:

- GET /api/applications/
- POST /api/applications/
- GET /api/applications/{id}/
- PATCH /api/applications/{id}/
- DELETE /api/applications/{id}/
- POST /api/applications/{id}/change-status/

Данные:
- id;
- name_application;
- about;
- organization;
- location;
- equipment;
- creator;
- executor;
- priority;
- status;
- deadline;
- date_create;
- created_at;
- updated_at.

Требования:
- список заявок ограничивать текущей organization;
- при создании creator = request.user;
- organization подставлять автоматически;
- location, equipment, executor, priority, status должны принадлежать или быть доступны в рамках текущей organization;
- при создании заявки создавать запись History_Application с comment="Заявка создана";
- при изменении статуса создавать запись History_Application;
- для engineer разрешить изменение статуса только своих заявок;
- права должны соответствовать текущей ролевой матрице.

## 4. API оборудования

Нужно добавить ручки для Equipment:

- GET /api/equipment/
- POST /api/equipment/
- GET /api/equipment/{id}/
- PATCH /api/equipment/{id}/
- DELETE /api/equipment/{id}/
- POST /api/equipment/{id}/change-status/

Данные:
- id;
- name_equipment;
- about;
- organization;
- location;
- status;
- type_equipment;
- external_id;
- date_input;
- created_at;
- updated_at.

Требования:
- список оборудования ограничивать текущей organization;
- location, status, type_equipment должны быть валидными;
- нельзя получить или изменить оборудование другой organization;
- при изменении статуса создавать запись History_Equipment;
- права должны соответствовать текущей ролевой матрице.

## 5. API пользователей

Нужно добавить ручки для пользователей организации:

- GET /api/users/
- GET /api/users/{id}/
- PATCH /api/users/{id}/, если это безопасно для текущей ролевой модели.

Данные пользователя:
- id;
- name;
- last_name;
- email;
- phone_number;
- is_active;
- organization_membership;
- role;
- department;
- position;
- date_reception.

Требования:
- возвращать только пользователей текущей organization;
- не отдавать пользователей других организаций;
- роль брать через OrganizationMembership;
- не использовать User.type_user;
- редактирование чужих пользователей доступно только admin;
- все роли могут просматривать и редактировать свой профиль, если такая логика будет добавлена в API.

## 6. Сериализаторы

Нужно добавить serializers.py.

Требования:
- создать отдельные serializers для Location, Application, Equipment, User/OrganizationMembership;
- не отдавать лишние служебные поля;
- поля organization и creator не должны приниматься от клиента напрямую, если они определяются сервером;
- добавить validate-методы для проверки принадлежности связанных объектов текущей organization;
- для read-only отображения можно добавить человекочитаемые поля:
  - status_name;
  - priority_name;
  - location_name;
  - executor_name;
  - organization_name.

## 7. Permissions

Нужно добавить DRF permissions или использовать текущий access/permissions слой.

Требования:
- API должен учитывать текущую ролевую матрицу;
- проверка должна быть на уровне viewset/action;
- нельзя ограничиваться скрытием полей;
- при отсутствии прав возвращать 403;
- при обращении к объекту другой organization возвращать 404 или 403, согласно текущему стилю проекта.

## 8. Swagger/OpenAPI-документация

Нужно добавить Swagger-документацию для API.

Требования:
- использовать drf-spectacular или drf-yasg, если один из пакетов уже есть в проекте;
- если ни один пакет не установлен, предпочтительно использовать drf-spectacular;
- добавить urls для документации:
  - /api/schema/
  - /api/docs/
- описать теги:
  - Locations;
  - Applications;
  - Equipment;
  - Users.
- добавить описания ручек;
- указать request/response serializers;
- для custom actions change-status добавить описание параметров.

## 9. Ограничения

- Не переводить текущий frontend на API.
- Не ломать Django Templates.
- Не добавлять JWT.
- Не менять текущую session-based auth.
- Не показывать данные других организаций.
- Не создавать публичные API без авторизации.
- Не трогать 3D-визуализацию.
- Не менять модели без необходимости.
- Не создавать миграции, если не меняются модели.
- Если нужно добавить зависимость DRF / drf-spectacular, обновить requirements.txt.

## Ожидаемый результат

После выполнения Codex должен показать:
- список измененных файлов;
- какие зависимости добавлены;
- какие serializers созданы;
- какие viewsets/API views созданы;
- какие urls добавлены;
- как реализована фильтрация по organization;
- как реализованы permissions;
- какие Swagger/OpenAPI endpoints доступны;
- как проверить API;
- команды для проверки проекта.