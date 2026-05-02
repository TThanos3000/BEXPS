# План разработки backend

## Цель
Разработать серверную часть Django-приложения для управления организациями, пользователями, локациями, 3D-моделями в JSON, оборудованием, заявками, историей изменений и файлами.

## Текущий контекст
В проекте уже есть часть backend и визуализация на Django Templates. Нужно развивать проект аккуратно, не ломая существующие страницы и текущую логику.

## Стек
Django
PostgreSQL
Django Templates с использованием bootstrap
В дальнейшем возможно Django REST Framework

## Основные сущности
- Organization
- User
- OrganizationMembership
- Location
- LocationModel
- Equipment
- Application

## Поддерживающие сущности
- Department
- OrganizationInvitation
- History_Application
- History_Equipment
- File

## Таблицы справочники
- ApplicationStatus
- ApplicationPriority
- EquipmentStatus
- EquipmentType

## Правила проектирования БД

- Статусы и типы не хранятся строками — используются справочники
- Все связи реализуются через ForeignKey
- JSON используется только для хранения 3D-модели
- Локации имеют иерархию через parent_id
- Роль пользователя хранится в OrganizationMembership

## Важные архитектурные решения
- Организация является верхним уровнем доступа
- Пользователь входит в организацию через OrganizationMembership
- Роль пользователя хранится в OrganizationMembership, а не в User
- Локации хранятся иерархически через parent_id
- 3D-модель хранится отдельно в LocationModel как единый JSON
- Модель не разбивается на отдельные BIM-элементы
- Equipment и Application привязываются к Location
- Все изменения БД делать через миграции

## Ограничения
- Не удалять существующую логику без отдельного решения
- Не ломать Django Templates
- Не переименовывать приложения без необходимости
- Не удалять миграции
- Не менять URL без причины
- После изменений запускать проверки