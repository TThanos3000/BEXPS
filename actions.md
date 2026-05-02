# Текущая задача

## Цель
Привести структуру базы данных Django-проекта к актуальной модели из plans.md:
- удалить устаревшие модели и поля
- обновить код, использующий эти модели
- обновить templates

## Целевая структура БД
Основные сущности:
- Organization
- User
- OrganizationMembership
- OrganizationInvitation
- Department
- Location
- LocationModel
- Equipment
- Application

Поддерживающие сущности:
- History_Application
- History_Equipment
- File

Справочники:
- ApplicationStatus
- ApplicationPriority
- EquipmentStatus
- EquipmentType

## Что нужно сделать

1. Найти модели, которых нет в целевой структуре:
   - например: Building, старые связи и устаревшие сущности

2. Найти устаревшие поля:
   - building_id
   - type_user
   - id_model
   - IdDepartment
   - Idapplication
   - IdHistory
   - IdEquipment внутри Location
   - file_id как string

3. Обновить код:
   - models.py
   - admin.py
   - forms.py
   - views.py
   - urls.py

4. Обновить templates:
   - удалить использование старых полей
   - заменить:
     - Building → Location (location_type="building")
     - User.type_user → OrganizationMembership.role
     - старые file_id → File модель

5. Подготовить миграции:
   - удалить устаревшие поля
   - сохранить данные, если возможно
   - не удалять старые миграции

## Ограничения

- Сначала сделать анализ, не менять код сразу
- Не удалять модели без проверки их использования
- Не ломать существующие страницы
- Не менять Django Templates без замены логики
- Не трогать 3D-визуализацию
- Не удалять миграции
- Новые изменения должны быть совместимы с текущими данными
- Если есть риск потери данных — указать это

## Ожидаемый результат

Codex должен:

1. Сначала выдать:
   - список устаревших моделей
   - список устаревших полей
   - где они используются
   - риски удаления

2. Затем (по отдельной команде):
   - удалить старые модели и поля
   - обновить templates
   - обновить backend-код
   - создать миграции

3. После изменений:
   - список измененных файлов
   - список удаленных сущностей
   - список обновленных templates
   - команды для проверки проекта