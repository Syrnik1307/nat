# Multi-Tenant Testing Guide

## Обзор тестовой инфраструктуры

Тесты для multi-tenant системы разделены по фазам, каждая фаза соответствует этапу из `MULTI_TENANT_IMPLEMENTATION_PLAN.md`.

### Файлы тестов

| Файл | Фаза | Кол-во тестов | Описание |
|---|---|---|---|
| `tenants/tests.py` | 0 (baseline) | 12 | Модели, middleware, API endpoints |
| `tenants/tests_smoke.py` | все | 7 | Smoke тесты после каждого шага |
| `tenants/tests_phase1.py` | 1 (FK) | 15 | Проверка school FK на моделях |
| `tenants/tests_phase2.py` | 2 (isolation) | 14 | Фильтрация данных по школе |
| `tenants/tests_phase3.py` | 3 (registration) | 11 | Регистрация + membership |
| `tenants/tests_phase4.py` | 4 (payments) | 10 | PaymentService per-school |
| `tenants/tests_e2e.py` | 9 (E2E) | 22 | Полные сценарии end-to-end |

**Итого: ~91 тест**

## Как запускать

### Все тесты разом
```bash
cd teaching_panel
python manage.py test tenants -v2
```

### По фазам (рекомендуется при разработке)
```bash
# Phase 0 — базовые тесты (ВСЕГДА должны проходить)
python manage.py test tenants.tests -v2

# Smoke тесты (прогонять ПОСЛЕ КАЖДОГО изменения)
python manage.py test tenants.tests_smoke -v2

# Phase 1 — FK на моделях (после миграции school FK)
python manage.py test tenants.tests_phase1 -v2

# Phase 2 — изоляция данных (после TenantViewSetMixin + ViewSets)
python manage.py test tenants.tests_phase2 -v2

# Phase 3 — регистрация (после RegisterView + membership)
python manage.py test tenants.tests_phase3 -v2

# Phase 4 — платежи (после PaymentService per-school)
python manage.py test tenants.tests_phase4 -v2

# E2E — полные сценарии (после Phase 1-4)
python manage.py test tenants.tests_e2e -v2
```

### Baseline + Smoke вместе
```bash
python manage.py test tenants.tests tenants.tests_smoke -v2
```

## Текущий статус

### Сейчас проходят (Phase 0 завершена):
- `tenants/tests.py` — 12/12 OK
- `tenants/tests_smoke.py` — 7/7 OK

### Будут проходить после реализации Phase 1:
- `tenants/tests_phase1.py` — тесты ожидают school FK на моделях Group, Homework, Subscription и др.

### Будут проходить после реализации Phase 2:
- `tenants/tests_phase2.py` — тесты ожидают `TENANT_ISOLATION_ENABLED=True` + TenantViewSetMixin на ViewSets

### Будут проходить после реализации Phase 3:
- `tenants/tests_phase3.py` — тесты ожидают авто-создание SchoolMembership при регистрации

### Будут проходить после реализации Phase 4:
- `tenants/tests_phase4.py` — тесты ожидают per-school payment credentials в PaymentService

### Будут проходить после Phase 1-4:
- `tenants/tests_e2e.py` — полные E2E сценарии

## Правило работы AI-агента

**ОБЯЗАТЕЛЬНО перед каждым PR / коммитом:**

```bash
# 1. Smoke тесты — если красные, СТОП
python manage.py test tenants.tests_smoke -v2

# 2. Baseline тесты — если красные, СТОП
python manage.py test tenants.tests -v2

# 3. Тесты текущей фазы
python manage.py test tenants.tests_phase{N} -v2
```

**Если smoke тесты красные — НЕ ПРОДОЛЖАЙ. Откатывай изменения.**

## Feature Flag

`TENANT_ISOLATION_ENABLED` в `settings.py`:
- По умолчанию: `False` (через env var `TENANT_ISOLATION_ENABLED=0`)
- Когда `False`: всё работает как раньше (single-tenant), тесты Phase 2+ проверяют обратную совместимость
- Когда `True`: TenantViewSetMixin фильтрует queryset по `request.school`

Включать **только после** завершения Phase 1 (FK) + Phase 2 (mixin).

## Структура тестов

### Phase 0 (tests.py) — Модели + Middleware
```
SchoolModelTests:
  test_0_01 — School модель создаётся
  test_0_02 — Default school находится
  test_0_03 — SchoolMembership + unique_together

TenantMiddlewareTests:
  test_0_04 — localhost → default school
  test_middleware_subdomain — anna.lectiospace.ru → School(slug='anna')
  test_middleware_unknown — nonexistent.lectiospace.ru → default school
  test_middleware_custom_domain — english-anna.com → School(custom_domain='english-anna.com')
  test_middleware_thread_local — set/get/clear работает

SchoolConfigAPITests:
  test_0_05 — GET /api/school/config/ → 200
  test_0_06 — GET /api/school/detail/ без токена → 401
  test_0_07 — to_frontend_config() содержит нужные поля
  test_0_08 — get_payment_credentials() fallback на PLATFORM_CONFIG
```

### Smoke (tests_smoke.py) — Критичные endpoints
```
test_smoke_01 — GET /api/health/ → 200
test_smoke_02 — POST /api/jwt/register/ → 201 + tokens
test_smoke_03 — GET /api/me/ → 200
test_smoke_04 — GET /api/groups/ → 200
test_smoke_05 — GET /api/homework/ → не 500/404
test_smoke_06 — GET /admin/ → 200/302
test_smoke_07 — GET /api/school/config/ → 200
```

### Phase 1 (tests_phase1.py) — School FK
```
TEST_1_01-07 — school FK существует на: Group, Homework, Subscription,
               ControlPoint, SupportTicket, StudentFinancialProfile, ScheduledMessage
TEST_1_08    — все существующие записи привязаны к default school (backfill)
TEST_1_09    — school FK nullable (null=True)
TEST_1_10    — school FK CASCADE behavior
TEST_1_11-12 — API GET/POST /api/groups/ работает (без изоляции)
TEST_1_13    — создание группы без school FK не ломает API
```

### Phase 2 (tests_phase2.py) — Изоляция данных
```
TEST_2_01-03 — flag=False: все данные видны, школа НЕ авто-присваивается
TEST_2_04-10 — flag=True: фильтрация по школе, кросс-школьные данные невидимы,
               superuser видит всё, perform_create авто-присваивает school,
               уроки/ДЗ изолированы, неактивный membership блокирует
```

### Phase 3 (tests_phase3.py) — Регистрация
```
TEST_3_01-02 — регистрация создаёт SchoolMembership (localhost, subdomain)
TEST_3_03    — роль в membership = role из запроса
TEST_3_04    — повторная регистрация не дублирует membership
TEST_3_05    — soft limit max_students
TEST_3_06    — логин НЕ создаёт membership
TEST_3_07    — /api/me/ включает информацию о школе
```

### Phase 4 (tests_phase4.py) — Платежи
```
TEST_4_01    — PaymentService без school работает (обратная совместимость)
TEST_4_02-03 — get_payment_credentials() own vs fallback
TEST_4_04    — без credentials → mock mode
TEST_4_05    — Subscription привязана к school
TEST_4_06    — webhook привязывает school через metadata
TEST_4_07    — return_url использует school URL
```

### E2E (tests_e2e.py) — Полные сценарии
```
22 теста покрывающих:
- Регистрация на двух школах (English Anna + Math Plus)
- Создание групп/ДЗ с авто-school
- Кросс-школьная изоляция данных
- Payment credentials per-school
- School config per subdomain
- /api/me/ с информацией о школе
- Default school isolation
- Деактивированная школа → 403
- Smoke с flag on/off
- Custom domain
- Feature flags
- Секреты НЕ утекают в /api/school/config/
```

## Частые проблемы

### DisallowedHost в middleware тестах
Тесты middleware используют `@override_settings(ALLOWED_HOSTS=['*'])` чтобы Django не блокировал subdomain hosts.

### Data migration не работает в тестах
Тестовая БД in-memory — data migrations не выполняются. Каждый тест сам создаёт default school через `setUp()`.

### URL /api/groups/ vs /api/schedule/groups/
Группы доступны по `/api/groups/` (через корневой router), НЕ `/api/schedule/groups/`.
