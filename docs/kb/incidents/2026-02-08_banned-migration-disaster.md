# ИНЦИДЕНТ: Tenant Migration Disaster

- **Дата**: 2026-02-08
- **Severity**: SEV0 (CRITICAL)
- **Автор**: n_syromyatnikov
- **Время восстановления**: ~4 часа

## Что произошло
Развёрнута система мультитенантности (tenants app), которая:
1. Добавила NOT NULL `tenant_id` в ~75 таблиц без данных
2. Сломала создание домашних заданий (500 ошибка)
3. Не была подключена в INSTALLED_APPS/MIDDLEWARE, но миграции были применены

## Root Cause
- Миграции с `AddField(null=False)` без `default` на таблицы с данными
- Отсутствие code review перед деплоем
- Отсутствие staging-тестирования

## Решение
- Ручной откат миграций через `RunSQL(DROP COLUMN tenant_id)`
- Восстановление из бэкапа для повреждённых таблиц

## Превентивные меры (НАВСЕГДА)
1. **ЗАПРЕЩЕНО**: tenants app, TenantMiddleware, tenant_id поля
2. Pre-commit хук блокирует tenant-код
3. settings.py runtime-проверка banned apps
4. .gitignore блокирует tenant-файлы
5. deploy_to_production.ps1 блокирует деплой с tenant-кодом
6. @db-guardian проверяет каждую миграцию

## Урок
**НИКОГДА не добавлять NOT NULL FK без данных в таблицы с данными.**
Всегда: AddField(null=True) → backfill → AlterField(null=False).
