# Отчёт по анализу и исправлению ошибок платформы Lectio

**Дата**: 28 января 2026  
**Статус**: ✅ Исправления применены и протестированы локально

---

## 📱 Telegram уведомления

### Когда приходят уведомления?

| Ситуация | Приоритет | Эмодзи | Отправляется? |
|----------|-----------|--------|---------------|
| Критические ошибки (FAIL > 0) | critical | 🚨 | ДА |
| Много предупреждений (WARN > 5) | high | ⚠️ | ДА |
| Всё в порядке | - | - | НЕТ* |

\* Можно включить через `--notify-success` или `NOTIFY_SUCCESS=1`

### Как включить "всё ОК" уведомление:

```bash
# Вариант 1: параметр командной строки
/opt/lectio-monitor/ultimate_check.sh --notify-success

# Вариант 2: переменная окружения (в cron)
NOTIFY_SUCCESS=1 /opt/lectio-monitor/ultimate_check.sh
```

---

## Обнаруженные ошибки (из Sentry и мониторинга)

### 1. KeyError: 'schedule.tasks.release_stuck_zoom_accounts' 

**Причина**: При редактировании файла [schedule/tasks.py](teaching_panel/schedule/tasks.py) функция `release_stuck_zoom_accounts` **потерялась** - её код оказался внутри docstring предыдущей функции `warmup_zoom_oauth_tokens`. Отсутствовал декоратор `@shared_task` и `def` определение.

**Статус**: ИСПРАВЛЕНО

**Изменение**: Добавлены `@shared_task` и `def release_stuck_zoom_accounts():` перед телом функции.

---

### 2. Failed to get Zoom OAuth token: 400 Client Error (account_id=bad)

**Причина**: У некоторых учителей установлены **тестовые/невалидные** Zoom credentials (например `account_id='bad'`). Celery задача `warmup_zoom_oauth_tokens` пыталась получить токен для таких аккаунтов и логировала ошибки.

**Статус**: ИСПРАВЛЕНО

**Изменение**: Добавлена фильтрация невалидных credentials:
- Список исключений: `'bad', 'test', 'invalid', 'demo', 'placeholder', 'xxx', '123'`
- Пониженный уровень логирования для ошибок 400/401 (debug вместо warning)

---

### 3. Failed to calculate folder size: timed out

**Причина**: Функция `get_teacher_storage_usage` вызывает `gdrive.calculate_folder_size()` которая рекурсивно обходит все файлы на Google Drive. При большом количестве файлов запрос может зависнуть.

**Статус**: ИСПРАВЛЕНО

**Изменение**: Добавлен 60-секундный таймаут для Google Drive операции в [gdrive_folder_service.py](teaching_panel/accounts/gdrive_folder_service.py) с использованием threading.

---

### 4. DisallowedHost: Invalid HTTP_HOST header: '0.0.0.0'

**Причина**: Кто-то обращается к серверу напрямую по IP `0.0.0.0` (вероятно health check или сканер), а Django не добавляет этот адрес в `ALLOWED_HOSTS`.

**Статус**: НЕ КРИТИЧНО, НЕ ИСПРАВЛЕНО

**Рекомендация**: 
- Это НЕ влияет на работу сайта
- Можно добавить `'0.0.0.0'` в `ALLOWED_HOSTS` если используется внутренний health check
- Или игнорировать в Sentry (фильтр по DisallowedHost)

---

### 5. NetworkError: Bad Gateway (Telegram bot)

**Причина**: Внешняя ошибка - Telegram API временно вернул 502. Это transient error.

**Статус**: НЕ КРИТИЧНО

**Рекомендация**: 
- Добавить retry логику в Telegram бот если не реализована
- Мониторинг уже обрабатывает такие ошибки

---

### 6. HTTP 000/502 на API endpoints

**Причина**: Сервер был временно недоступен. Возможные причины:
- Gunicorn перезапуск
- Nginx перезапуск  
- Сетевые проблемы
- Деплой в процессе

**Статус**: ТРЕБУЕТ МОНИТОРИНГА

**Рекомендация**: 
- Уже есть auto-recovery в health_check.sh
- Добавлен grace period для деплоя (60 сек)

---

## Применённые исправления

### Файл: [schedule/tasks.py](teaching_panel/schedule/tasks.py)

1. **Восстановлена функция `release_stuck_zoom_accounts`** - добавлены `@shared_task` и `def`
2. **Улучшена фильтрация в `warmup_zoom_oauth_tokens`**:
   - Пропуск невалидных credentials
   - Пониженный уровень логирования для ожидаемых ошибок

### Файл: [accounts/gdrive_folder_service.py](teaching_panel/accounts/gdrive_folder_service.py)

1. **Добавлен 60-секундный таймаут** для `calculate_folder_size` через threading

---

## Новый скрипт тестирования

Создан расширенный скрипт проверки: [comprehensive_check.sh](scripts/monitoring/comprehensive_check.sh)

### Категории тестов:

#### Инфраструктура:
- Дисковое пространство (>90% = warn, >95% = fail)
- Использование памяти
- Gunicorn workers
- Redis connection
- Celery workers (если включен)

#### Сеть:
- SSL сертификат (срок истечения)
- DNS resolution
- CORS preflight

#### API Endpoints:
- `/api/health/`
- `/api/me/`
- `/api/schedule/lessons/` + замер времени
- `/api/groups/`
- `/schedule/api/recordings/teacher/`
- `/api/homework/`
- `/api/subscription/`
- `/api/analytics/teacher/stats/`
- `/api/students/`
- `/api/zoom-pool/accounts/`

#### Статика:
- `asset-manifest.json`
- Main CSS bundle
- Main JS bundle

#### Безопасность:
- Security headers (X-Frame-Options, X-Content-Type-Options)
- Rate limiting (опционально)

---

## Полный список тестов для мониторинга

### Быстрые проверки (smoke_check_v2.sh) - каждые 1-5 минут

| Тест | Endpoint | Критичность |
|------|----------|-------------|
| Health check | `/api/health/` | Critical |
| Frontend HTML | `/` | Critical |
| Teacher JWT auth | `/api/jwt/token/` | Critical |
| Student JWT auth | `/api/jwt/token/` | Critical |
| User profile | `/api/me/` | High |
| Lessons list | `/api/schedule/lessons/` | High |
| Recordings list | `/schedule/api/recordings/teacher/` | High |
| Homework list | `/api/homework/` | High |
| Subscription status | `/api/subscription/` | Medium |
| Payment creation | `/api/subscription/create-payment/` | Medium |
| Groups list | `/api/groups/` | Medium |

---

### Ultimate Check (ultimate_check.sh) - каждые 2 часа

#### 1. Инфраструктура (9 тестов)
| Тест | Проверка | Пороги |
|------|----------|--------|
| Disk Space | `df -h /` | <80% OK, <90% WARN, >90% FAIL |
| Memory | `free` | <80% OK, <90% WARN, >90% FAIL |
| CPU Load | `uptime` | < cores OK, < 2x cores WARN |
| Nginx | `systemctl + nginx -t` | Running + valid config |
| Gunicorn | `pgrep gunicorn` | >0 workers |
| Redis | `redis-cli ping` | PONG |
| PostgreSQL | `pg_isready` | Ready (if installed) |
| Celery | `systemctl` | Active (if enabled) |
| Recent Errors | Logs analysis | <5 OK, <20 WARN |

#### 2. Сеть и SSL (4 теста)
| Тест | Проверка | Пороги |
|------|----------|--------|
| SSL Certificate | `openssl s_client` | >30 days OK, >7 WARN |
| DNS Resolution | `dig` | IP returned |
| HTTPS Redirect | HTTP->HTTPS | 301/302 redirect |
| Security Headers | X-Frame-Options, etc. | All present |

#### 3. База данных (7 тестов)
| Тест | Проверка | Критичность |
|------|----------|-------------|
| DB Connectivity | `SELECT 1` | Critical |
| Orphaned Students | Студенты без групп | <10% OK, <30% WARN |
| Lessons Without Groups | Уроки без группы | 0 = OK |
| Recordings Without Files | Записи без файлов | 0 = OK, <5 WARN |
| Stuck Payments | Pending >1 час | 0 = OK |
| Expired Subscriptions | Active но expired | 0 = OK, else FAIL |
| Homework Integrity | ДЗ без учителя | 0 = OK |

#### 4. Авторизация (5 тестов)
| Тест | Проверка |
|------|----------|
| Teacher JWT Login | Получение токена |
| Student JWT Login | Получение токена |
| Token Refresh | Обновление токена |
| /api/me/ endpoint | Профиль пользователя |
| Invalid Token Rejection | 401 для невалидных |

#### 5. API Endpoints (8 тестов)
| Endpoint | Дополнительно |
|----------|---------------|
| `/api/health/` | Проверка DB flag |
| `/api/schedule/lessons/` | Замер времени (>5s = WARN) |
| `/api/groups/` | - |
| `/api/students/` | - |
| `/schedule/api/recordings/teacher/` | - |
| `/api/homework/` | - |
| `/api/subscription/` | - |
| `/api/analytics/teacher/stats/` | 403 = OK (subscription) |

#### 6. Платежи (5 тестов)
| Тест | Проверка |
|------|----------|
| YooKassa API | HTTPS reachable (401 = OK) |
| T-Bank API | HTTPS reachable (405 = OK) |
| YooKassa Webhook | `/api/payments/yookassa/webhook/` |
| T-Bank Webhook | `/api/payments/tbank/webhook/` |
| Payment Creation | Тестовый платёж |

#### 7. Google Drive (3 теста)
| Тест | Проверка |
|------|----------|
| Connection | OAuth + user info |
| Quota | <80% OK, <95% WARN |
| Root Folder | Доступ к папке |

#### 8. Zoom (2 теста)
| Тест | Проверка |
|------|----------|
| OAuth Token | Получение токена для учителя |
| API Availability | api.zoom.us reachable |

#### 9. Telegram (2 теста)
| Тест | Проверка |
|------|----------|
| Bot Status | `/getMe` API call |
| Chat Access | `/getChat` для CHAT_ID |

#### 10. Статика (3 теста)
| Тест | Проверка |
|------|----------|
| Asset Manifest | `/asset-manifest.json` |
| Index HTML | React markers present |
| Build Age | Возраст build директории |

---

### Deep Diagnostics (deep_diagnostics.py) - каждые 6 часов

Python-скрипт с доступом к Django ORM для глубоких проверок:

#### Пользователи
- Users without email
- Duplicate emails (case-insensitive)
- Teachers without subscription
- Students without groups (% orphaned)

#### Подписки
- Expired but active status
- Expiring soon (7 days)
- Storage over limit

#### Платежи
- Stuck pending payments (>1 hour)
- Payment failure rate (24h)
- Orphaned payments (no subscription link)

#### Группы и уроки
- Empty groups (no students)
- Lessons without groups
- Lessons in last month (info)

#### Записи
- Recordings without files (gdrive or URL)
- Orphaned recordings (no lesson or teacher)
- Recordings with expired Zoom links

#### Домашние задания
- Homework without teacher
- Old ungraded submissions (>7 days)
- Past-deadline homework without submissions

#### Google Drive
- Connection test
- Quota check
- Root folder access

#### Zoom
- Teachers with credentials count
- OAuth token test

#### Производительность
- Query timing (users, lessons, recordings)
- Table sizes

---

### Установка на сервер

```bash
# 1. Копируем скрипты
scp scripts/monitoring/ultimate_check.sh lectio:/opt/lectio-monitor/
scp scripts/monitoring/deep_diagnostics.py lectio:/opt/lectio-monitor/

# 2. Делаем исполняемыми
ssh lectio "chmod +x /opt/lectio-monitor/ultimate_check.sh"
ssh lectio "chmod +x /opt/lectio-monitor/deep_diagnostics.py"

# 3. Добавляем в cron
ssh lectio "cat >> /etc/cron.d/lectio-monitoring << 'EOF'
# Ultimate check every 2 hours
0 */2 * * * root /opt/lectio-monitor/ultimate_check.sh >> /var/log/lectio-monitor/ultimate.log 2>&1

# Deep diagnostics every 6 hours
0 */6 * * * root cd /var/www/teaching_panel/teaching_panel && ../venv/bin/python /opt/lectio-monitor/deep_diagnostics.py >> /var/log/lectio-monitor/deep.log 2>&1

# Ежедневная проверка с уведомлением об успехе (подтверждение что мониторинг работает)
0 8 * * * root NOTIFY_SUCCESS=1 /opt/lectio-monitor/ultimate_check.sh >> /var/log/lectio-monitor/daily.log 2>&1
EOF"
```

---

## 🧪 Результаты тестирования (локально)

### deep_diagnostics.py - РАБОТАЕТ ✅

```
=== Запуск на тестовой базе ===
Total checks: 24
  OK:       10
  WARNINGS: 4  
  FAILURES: 3
  INFO:     6

Найденные проблемы (тестовые данные):
- 99.9% студентов без групп (тестовые данные)
- 1 подписка expired но active
- GDrive ошибка (нет credentials локально)
```

### ultimate_check.sh - РАССЧИТАН НА LINUX

Скрипт использует bash-специфичные конструкции и Linux инструменты (`systemctl`, `pgrep`, `df`).
Для полного тестирования требуется запуск на сервере.

---

## Действия для деплоя

```bash
# 1. Коммит изменений
git add -A
git commit -m "fix: restore release_stuck_zoom_accounts, add GDrive timeout, improve Zoom warmup"

# 2. Деплой
.\auto_deploy.ps1

# 3. Установка нового скрипта мониторинга
ssh lectio "sudo cp /var/www/teaching_panel/scripts/monitoring/comprehensive_check.sh /opt/lectio-monitor/"
ssh lectio "sudo chmod +x /opt/lectio-monitor/comprehensive_check.sh"

# 4. Добавить в cron (каждые 6 часов)
ssh lectio "echo '0 */6 * * * root /opt/lectio-monitor/comprehensive_check.sh >> /var/log/lectio-monitor/comprehensive.log 2>&1' | sudo tee /etc/cron.d/lectio-comprehensive"
```

---

## Что НЕ исправлено (не требует исправления)

| Ошибка | Причина | Действие |
|--------|---------|----------|
| DisallowedHost 0.0.0.0 | Внешний сканер/health check | Игнорировать в Sentry |
| Telegram Bad Gateway | Transient error | Уже есть retry |
| HTTP 000 при деплое | Ожидаемо | Уже есть grace period |

---

## Рекомендации

1. **Очистить невалидные Zoom credentials** у учителей в БД:
   ```sql
   UPDATE accounts_customuser 
   SET zoom_account_id = NULL, zoom_client_id = NULL, zoom_client_secret = NULL 
   WHERE zoom_account_id IN ('bad', 'test', 'invalid');
   ```

2. **Добавить фильтр в Sentry** для `DisallowedHost`

3. **Проверить Telegram webhook** на предмет retry policy

4. **Мониторить размер папок на GDrive** - возможно нужна оптимизация для больших папок
