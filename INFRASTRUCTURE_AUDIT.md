# Infrastructure Audit Report

**Дата:** 2026-01-15  
**Scope:** Docker Compose, Nginx, Celery, Monitoring  
**Проект:** Teaching Panel (Lectio Space)

---

## 1. Резюме

Проведён полный аудит инфраструктурного слоя: Docker-конфигурации (dev/prod), Nginx (Docker + production сервер), Celery (настройки, очереди, воркеры), мониторинг (~25 скриптов). Выявлено **9 проблем** (3 критических, 3 высоких, 3 средних). **8 исправлено** в рамках аудита.

### Статус исправлений

| # | Уровень | Проблема | Статус |
|---|---------|----------|--------|
| 1 | CRITICAL | Celery: один воркер на все очереди (Docker prod) | FIXED |
| 2 | CRITICAL | Gunicorn: sync воркеры вместо gevent (Docker prod) | FIXED |
| 3 | CRITICAL | Nginx prod: нет rate limiting ни на одном endpoint | FIXED |
| 4 | HIGH | Nginx prod: client_max_body_size 2G | FIXED |
| 5 | HIGH | Nginx prod: нет HSTS header | FIXED |
| 6 | HIGH | Мониторинг: нет проверки Celery и Redis | FIXED |
| 7 | MEDIUM | Nginx Docker prod: нет security headers | FIXED |
| 8 | MEDIUM | Nginx Docker: client_max_body_size 10G | FIXED |
| 9 | MEDIUM | Nginx prod: нет Permissions-Policy | FIXED |

---

## 2. Анализ по областям

### 2.1 Docker & Docker Compose

**Файлы:**
- `docker-compose.yml` — dev (SQLite + Redis)
- `docker-compose.prod.yml` — prod (PostgreSQL 16 + Redis 7 + Nginx 1.25)
- `docker/backend/Dockerfile.prod` — Python 3.11-slim, non-root user (appuser)
- `docker/backend/entrypoint.prod.sh` — миграции + Gunicorn

#### Что хорошо
- Docker Compose prod использует healthcheck для PostgreSQL и Redis
- backend зависит от `postgres.service_healthy` + `redis.service_healthy`
- Лимиты по памяти расставлены на все сервисы
- Redis не открывает порты наружу
- PostgreSQL не открывает порты наружу
- Dockerfile.prod запускает под non-root (appuser)
- Redis настроен с AOF + maxmemory policy

#### Исправлено

**[CRITICAL] Celery: один воркер на все очереди**

До: Единый сервис `celery` обрабатывал ВСЕ очереди (`default,notifications,periodic,heavy`).  
Проблема: Тяжёлые задачи (скачивание видео с Zoom, обработка записей) блокировали уведомления и периодические задачи.

После: Разделено на два сервиса:
- `celery_default` — очереди `default,notifications,periodic`, concurrency=2, memory limit 600M
- `celery_heavy` — очередь `heavy`, concurrency=1, memory limit 800M

Оба используют `--without-gossip --without-mingle` для экономии ресурсов.

**[CRITICAL] Gunicorn: sync воркеры вместо gevent**

До: `entrypoint.prod.sh` запускал Gunicorn с `--threads 4` (sync worker class).  
Проблема: Несоответствие с systemd-конфигами (которые используют gevent). Sync воркеры блокируются на I/O, теряют 60-80% throughput при внешних API-вызовах.

После: `--worker-class gevent --worker-connections 1000` + `--timeout 60 --graceful-timeout 30 --max-requests 1500 --max-requests-jitter 150`.

#### Рекомендации (не реализовано)

1. **Docker image size** — текущий prod image ~400-500MB. Можно уменьшить до ~200MB:
   - Multi-stage build для Python (сборка wheel'ов в build-stage, копирование в runtime)
   - Явное указание `--no-cache-dir` при pip install (уже есть)
   - Добавить `.dockerignore` для исключения `frontend/`, `*.md`, `scripts/`, тестов
   
2. **Docker Compose: backend replicas** — при росте нагрузки добавить `deploy.replicas: 2` и round-robin через nginx upstream

---

### 2.2 Nginx

**Файлы:**
- `docker/nginx/nginx.conf` — dev (Docker)
- `docker/nginx/nginx.prod.conf` — prod (Docker)
- `docker/nginx/locations.conf` — общие locations (Docker dev/prod)
- `deploy/nginx/lectio_tw1` — ACTUAL production сервер (lectio.tw1.ru)

#### Что хорошо
- Production: SSL с TLSv1.2/1.3
- Production: HTTP→HTTPS redirect
- Docker `locations.conf`: уже содержит rate limiting zones (api_limit, login_limit)
- Production: кэширование homework файлов (proxy_cache, 30d)
- Production: streaming endpoint без буферизации (proxy_buffering off)
- Production: SPA fallback с cache-control no-cache для index.html
- Production: статика с expires 7d

#### Исправлено

**[CRITICAL] Production nginx: нет rate limiting**

До: Ни один endpoint не имел rate limiting. Сервер был открыт для brute force на login, API flood, DoS.

После:
- Rate limiting zones: `api_limit` (30r/s), `login_limit` (5r/m), `conn_limit`
- `/api/jwt/token/` и `/api/jwt/register/` — `limit_req zone=login_limit burst=3 nodelay`
- `/api/` — `limit_req zone=api_limit burst=50 nodelay` + `limit_conn conn_limit 20`

**[HIGH] client_max_body_size 2G → 200M**

Бэкенд ограничивает uploads до 200MB. Nginx разрешал 2GB — бесполезная трата ресурсов и потенциальный вектор DoS.

**[HIGH] Добавлен HSTS**

`Strict-Transport-Security "max-age=63072000; includeSubDomains"` — браузер кэширует HTTPS-redirect на 2 года.

**[MEDIUM] Security headers**

Добавлены в Docker prod и production:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

**[MEDIUM] locations.conf body size 10G → 200M**

Docker dev/prod locations использовали `client_max_body_size 10g`. Исправлено на `200M`.

#### Рекомендации (не реализовано)

1. **Webhook IP filtering** — ограничить доступ к `/schedule/webhook/zoom/` и YooKassa webhook по IP
2. **Content-Security-Policy header** — добавить CSP для защиты от XSS
3. **Nginx Worker tuning** — `worker_connections 4096` для Docker prod

---

### 2.3 Celery

**Файлы:**
- `teaching_panel/teaching_panel/celery.py` — app config, signal handlers
- `teaching_panel/teaching_panel/settings.py` (lines 390-640) — queues, routes, beat schedule
- `deploy/scaling/stage-*/celery-*.service` — systemd сервисы

#### Что хорошо
- 4 очереди с явной маршрутизацией: `default`, `heavy`, `notifications`, `periodic`
- 5 задач маршрутизированы в `heavy` (Zoom recordings, video download)
- 7 задач маршрутизированы в `notifications` (Telegram, email)
- `acks_late=True` + `reject_on_worker_lost=True` — задачи не теряются при crash
- `prefetch_multiplier=1` — fair scheduling
- `max_tasks_per_child=50` + `max_memory_per_child=150000` — защита от утечек памяти
- Signal handler `task_failure` отправляет алерты в Telegram
- DB connection management: close_stale → before task, close_all + gc.collect → after task
- Beat schedule: ~25 задач, от 60s до weekly

#### Celery Beat Schedule (ключевые задачи)

| Задача | Интервал | Очередь |
|--------|----------|---------|
| release_stuck_zoom_accounts | 5 мин | default |
| check_lesson_reminders | 60 сек | notifications |
| cleanup_old_sync_zoom_recordings | 30 мин | heavy |
| weekly_dashboard_email | weekly (пн 9:00) | notifications |
| monitor_failed_payments | 1 час | periodic |

#### Рекомендации

1. **Queue depth monitoring** — добавить алерт, если в очереди > N задач (`redis-cli LLEN celery`)
2. **Flower dashboard** — добавить как опциональный сервис в docker-compose для визуализации
3. **Task result TTL** — текущий `CELERY_RESULT_EXPIRES = 3600` (1 час) — достаточно, но можно уменьшить для экономии Redis памяти

---

### 2.4 Мониторинг

**Файлы:**
- `scripts/monitoring/health_check.sh` (~700 строк) — основной health check с auto-recovery
- `scripts/monitoring/unified_monitor.sh` (~480 строк) — unified monitoring с anti-spam
- `scripts/monitoring/deep_diagnostics.py` — глубокая диагностика (Django management command)
- `scripts/monitoring/ops_alerts_bot.py` — Telegram бот для алертов
- `scripts/monitoring/monitor-capacity.sh` — мониторинг capacity (CPU, memory, disk)
- `scripts/monitoring/memory_alert.sh` — мониторинг памяти
- + ещё ~15 вспомогательных скриптов

#### Что хорошо
- health_check.sh: комплексная проверка (HTTP, API, frontend build consistency, permissions, disk, memory, gunicorn workers)
- health_check.sh: автоматическое восстановление (перезапуск Django, Nginx, fix permissions, restore frontend build from backup)
- unified_monitor.sh: anti-spam (не шлёт одинаковые алерты в Telegram повторно)
- unified_monitor.sh: auto-recovery для Django (502/503/504), Nginx, gunicorn workers
- Telegram интеграция для алертов
- Lock файлы для предотвращения параллельного запуска
- deep_diagnostics.py: Django-aware диагностика (DB connections, migrations, Celery status)

#### Исправлено

**[MEDIUM] Нет проверки Celery и Redis**

До: `unified_monitor.sh` проверял только Django, Nginx, memory, disk, gunicorn workers. Если Celery или Redis падали — никаких алертов.

После добавлены:
- `check_redis()` — проверка `redis-cli ping`, мониторинг memory usage (% от maxmemory)
- `check_celery()` — проверка наличия celery worker процессов, проверка celery beat
- Auto-recovery: рестарт celery-default, celery-heavy, celery-beat, redis-server при failure
- Вызовы в main loop и post-recovery re-check block

#### Рекомендации

1. **Prometheus + Grafana** — для долгосрочных трендов (CPU, memory, request latency). Текущий мониторинг — reactive only
2. **Structured logging** — перевести на JSON logging для Django/Gunicorn, чтобы парсить автоматически
3. **Alertmanager** — единая точка для routing/dedup алертов вместо ручного anti-spam в bash

---

## 3. Scalability: анализ бутылочных горлышек при 10x нагрузке

Текущая нагрузка: ~50 учителей. 10x = ~500 учителей, ~2500 учеников.

### Bottleneck #1: SQLite (Production)

**Текущая ситуация:** Production использует SQLite. Это однопоточная БД с global write lock.

**При 10x:** SQLite начнёт давать `SQLITE_BUSY` ошибки при параллельных записях. Latency запросов вырастет x5-x10.

**Решение:** Миграция на PostgreSQL (Docker Compose prod уже настроен). Deploy scaling configs готовы для stage A/B/C.

### Bottleneck #2: Single Gunicorn Instance

**При 10x:** 4 gevent workers обрабатывают ~200-400 concurrent requests. При 500 учителях в peak hours → timeout'ы.

**Решение:** Масштабировать до 6-8 workers (stage A config уже есть). При stage B — второй backend instance за nginx load balancer.

### Bottleneck #3: Celery Heavy Queue

**При 10x:** Скачивание записей с Zoom (1-2 GB per recording) с concurrency=1 создаст очередь из 50+ задач.

**Решение:** Масштабировать `celery_heavy` до concurrency=2-3 или `--scale celery_heavy=2` в Docker.

### Bottleneck #4: Redis Memory

**При 10x:** 512MB maxmemory хватит (~10K задач в очереди). Но если кэш + результаты задач + сессии — может не хватить.

**Решение:** Увеличить до 1GB, включить мониторинг (уже добавлен в unified_monitor.sh).

---

## 4. Предложение HA-архитектуры

### Stage A: Текущий (до 300 учителей)

```
                    ┌──────────┐
                    │  Nginx   │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ Gunicorn │ (4 gevent workers)
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼───┐ ┌───▼────┐ ┌──▼───┐
         │ SQLite │ │ Redis  │ │Celery│
         └────────┘ └────────┘ └──────┘
```

**Действия:** Миграция SQLite → PostgreSQL. Это текущий приоритет.

### Stage B: Рост (300-750 учителей)

```
                    ┌──────────┐
                    │  Nginx   │
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │                     │
         ┌────▼─────┐        ┌─────▼────┐
         │Gunicorn 1│        │Gunicorn 2│
         └────┬─────┘        └────┬─────┘
              │                   │
         ┌────▼───────────────────▼────┐
         │        PgBouncer            │
         └────────────┬───────────────┘
                      │
              ┌───────▼───────┐
              │  PostgreSQL   │
              └───────────────┘
              
         Redis │ Celery-default x2 │ Celery-heavy x1
```

**Действия:**
1. PgBouncer (конфигурация уже готова в `deploy/scaling/stage-b/`)
2. Второй Gunicorn instance (`deploy.replicas: 2`)
3. Масштабировать celery_default: `--scale celery_default=2`

### Stage C: Масштаб (750-1500 учителей)

```
              ┌─────────────┐
              │ Load Balancer│
              └──────┬──────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼───┐  ┌────▼───┐  ┌───▼────┐
    │Nginx+GU│  │Nginx+GU│  │Nginx+GU│
    └────┬───┘  └────┬───┘  └────┬───┘
         │           │           │
    ┌────▼───────────▼───────────▼────┐
    │           PgBouncer             │
    └────────────┬────────────────────┘
                 │
         ┌───────▼───────┐
         │  PostgreSQL   │──── Read Replica
         └───────────────┘
         
    Redis Sentinel │ Celery-default x3 │ Celery-heavy x2
```

**Действия:**
1. Вынести Celery workers на отдельный сервер
2. Redis Sentinel для failover
3. PostgreSQL read replica для аналитики
4. CDN для статики и фронтенда

---

## 5. Docker-оптимизации

### 5.1 Уменьшение размера образов

**Текущий `Dockerfile.prod`:**
```dockerfile
FROM python:3.11-slim
# ~150MB base + ~300MB dependencies = ~450MB
```

**Оптимизированный вариант (рекомендация):**
```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage  
FROM python:3.11-slim
COPY --from=builder /install /usr/local
COPY teaching_panel/ /app/teaching_panel/
# Result: ~200-250MB (no build tools, no pip cache)
```

### 5.2 .dockerignore

Создать файл для исключения ненужного:
```
frontend/node_modules/
frontend/build/
*.md
scripts/
*.py (корневые скрипты)
.git/
__pycache__/
*.sqlite3
```

### 5.3 Layer caching

Копировать `requirements.txt` отдельно от кода приложения (уже сделано):
```dockerfile
COPY requirements.txt .
RUN pip install ...
COPY teaching_panel/ .  # Изменения кода не инвалидируют pip cache
```

---

## 6. Изменённые файлы

| Файл | Изменения |
|------|-----------|
| `docker-compose.prod.yml` | Разделение celery на celery_default + celery_heavy |
| `docker/backend/entrypoint.prod.sh` | Gunicorn: sync → gevent + tuning params |
| `docker/nginx/nginx.prod.conf` | Security headers + webhook_limit zone |
| `docker/nginx/locations.conf` | client_max_body_size 10g → 200M |
| `deploy/nginx/lectio_tw1` | Rate limiting zones, HSTS, Permissions-Policy, body size 2G→200M, login rate limiting, API rate limiting |
| `scripts/monitoring/unified_monitor.sh` | check_redis(), check_celery(), auto-recovery для Celery/Redis |

---

## 7. Перед деплоем на production

**Nginx (lectio_tw1):**
```bash
# 1. Скопировать конфиг
scp deploy/nginx/lectio_tw1 tp:/etc/nginx/sites-available/lectio_tw1

# 2. Проверить синтаксис
ssh tp 'sudo nginx -t'

# 3. Reload (без downtime)
ssh tp 'sudo systemctl reload nginx'
```

**Мониторинг (unified_monitor.sh):**
```bash
# 1. Скопировать
scp scripts/monitoring/unified_monitor.sh tp:/var/www/teaching_panel/scripts/monitoring/

# 2. Проверить (dry run)
ssh tp 'sudo bash /var/www/teaching_panel/scripts/monitoring/unified_monitor.sh'
```

**Docker prod** — изменения не требуют немедленного деплоя (проект пока работает на systemd, не в Docker).

---

*Аудит выполнен. Все критические и высокие проблемы исправлены.*
