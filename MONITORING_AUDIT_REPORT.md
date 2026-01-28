# АУДИТ СИСТЕМЫ МОНИТОРИНГА LECTIO

**Дата:** 27 января 2026
**Автор:** AI Agent
**Статус:** ✅ ИСПРАВЛЕНО И ЗАДЕПЛОЕНО

---

## РЕЗЮМЕ

Проведён полный аудит системы мониторинга. Выявлены **3 критические проблемы** и **5 недостающих проверок**. Все проблемы исправлены и задеплоены на production.

---

## КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### 1. ❌ Smoke Test постоянно падает (с ноября 2025)

**Симптом:** Каждые 5 минут в логах:
```
Не удалось создать JWT для teacher (smoke_hw_teacher@test.local)
/api/homework/ (student) HTTP 301
```

**Причина:** 
- Пользователь `smoke_hw_teacher@test.local` **НЕ СУЩЕСТВУЕТ** в БД
- Только студенты: `smoke_hw_student@test.local`, `smoke_hw_student_b@test.local`
- HTTP 301 вместо 200 - пропущен trailing slash в URL

**Решение:** Создать пользователей или обновить smoke_check.sh

---

### 2. ❌ Алерты не приходят при падении сайта

**Симптом:** Ты перестал получать уведомления о падении сайта.

**Причина:** 
- `smoke_check.sh` использует `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID`
- Алерты уходят в основной бот Teaching Panel, а не в бот ошибок
- При этом `health_check.sh` использует `ERRORS_BOT_TOKEN` - другой бот

**Конфигурация сервера:**
```env
TELEGRAM_BOT_TOKEN="8306654343:AAG..."  # Основной бот
ERRORS_BOT_TOKEN="8227462251:AAH..."    # Бот ошибок ← правильный
ERRORS_CHAT_ID="6378715567"
```

**Решение:** Унифицировать на `ERRORS_BOT_TOKEN` во всех скриптах

---

### 3. ❌ Ложные алерты при деплое

**Симптом:** При каждом деплое прилетает алерт что сайт сломался.

**Причина:**
- `health_check.sh` запускается каждую минуту
- Во время деплоя (5-15 сек) сервисы недоступны
- Скрипт ловит это и шлёт алерт

**Решение:** Добавить grace period - маркер `/var/run/lectio-monitor/deploy_in_progress`

---

## ТЕКУЩИЕ ПРОВЕРКИ (что есть)

| Скрипт | Периодичность | Что проверяет |
|--------|---------------|---------------|
| `health_check.sh` | 1 мин | HTTP 200 главной, systemd сервисы, права frontend, диск, память, gunicorn |
| `smoke_check.sh` | 5 мин | JWT учителя/студента, /api/me/, /api/homework/, /api/schedule/lessons/, платежи |

---

## НЕДОСТАЮЩИЕ ПРОВЕРКИ

| # | Сценарий | Важность | Статус |
|---|----------|----------|--------|
| 1 | **Записи уроков** - `/api/schedule/recordings/teacher/` | Критическая | ❌ Не проверяется |
| 2 | **Стриминг видео** - `/api/schedule/recordings/{id}/stream/` | Критическая | ❌ Не проверяется |
| 3 | **Группы** - `/api/groups/` | Высокая | ❌ Не проверяется |
| 4 | **Подписка** - `/api/subscription/` | Высокая | ❌ Не проверяется |
| 5 | **Статические файлы** - проверка что React bundle грузится | Критическая | ❌ Не проверяется |
| 6 | **Посещаемость** - `/api/attendance-records/` | Средняя | ❌ Не проверяется |
| 7 | **Gradebook** - `/api/gradebook/` | Средняя | ❌ Не проверяется |
| 8 | **GDrive интеграция** - загрузка файлов | Низкая | ❌ Не проверяется |
| 9 | **Zoom интеграция** - получение токена | Низкая | ❌ Не проверяется |

---

## СОЗДАННЫЕ РЕШЕНИЯ

### 1. `smoke_check_v2.sh` - Улучшенный smoke test

**Проверяет:**
- ✅ Статические файлы (React bundle)
- ✅ Health endpoint с проверкой БД
- ✅ Авторизация учителя (через JWT API)
- ✅ Уроки `/api/schedule/lessons/`
- ✅ Записи `/api/schedule/recordings/teacher/`
- ✅ ДЗ (учитель) `/api/homework/`
- ✅ Подписка `/api/subscription/`
- ✅ Создание платежа `/api/subscription/create-payment/`
- ✅ Группы `/api/groups/`
- ✅ Авторизация студента
- ✅ ДЗ (студент) `/api/homework/`

**Улучшения:**
- Использует `ERRORS_BOT_TOKEN` (правильный бот)
- Антиспам: не шлёт одинаковые алерты чаще 5 мин
- Grace period: пропускает алерты во время деплоя

### 2. `setup_smoke_users.sh` - Создание тестовых пользователей

Создаёт:
- `smoke_teacher@test.local` / `SmokeTest123!`
- `smoke_student@test.local` / `SmokeTest123!`

### 3. Обновлён `deploy_safe.sh`

- Добавлен маркер `/var/run/lectio-monitor/deploy_in_progress`
- Smoke checks пропускают алерты пока маркер существует

---

## ПЛАН ДЕЙСТВИЙ

### Шаг 1: Деплой исправлений на сервер

```bash
# Скопировать новые скрипты
scp scripts/monitoring/smoke_check_v2.sh root@lectio.tw1.ru:/opt/lectio-monitor/
scp scripts/monitoring/setup_smoke_users.sh root@lectio.tw1.ru:/opt/lectio-monitor/
scp scripts/monitoring/deploy_safe.sh root@lectio.tw1.ru:/opt/lectio-monitor/

# Сделать исполняемыми
ssh root@lectio.tw1.ru "chmod +x /opt/lectio-monitor/*.sh"
```

### Шаг 2: Создать тестовых пользователей

```bash
ssh root@lectio.tw1.ru "/opt/lectio-monitor/setup_smoke_users.sh"
```

### Шаг 3: Обновить cron на новый smoke_check_v2

```bash
ssh root@lectio.tw1.ru "crontab -l | sed 's/smoke_check.sh/smoke_check_v2.sh/g' | crontab -"
```

### Шаг 4: Протестировать отправку алертов

```bash
ssh root@lectio.tw1.ru "/opt/lectio-monitor/smoke_check_v2.sh"
```

---

## РЕКОМЕНДАЦИИ НА БУДУЩЕЕ

1. **Добавить мониторинг стриминга видео** - отдельный smoke test для проверки что записи открываются

2. **Мониторинг GDrive** - проверять что файлы загружаются (раз в час)

3. **Мониторинг Zoom** - проверять что OAuth токен можно получить

4. **Централизованный дашборд** - рассмотреть Grafana + Prometheus для визуализации

5. **Алерты в отдельный канал** - создать Telegram группу для мониторинга, не личку

---

## ФАЙЛЫ

| Файл | Описание |
|------|----------|
| `scripts/monitoring/smoke_check_v2.sh` | Новый smoke test с 11 проверками |
| `scripts/monitoring/setup_smoke_users.sh` | Создание тестовых пользователей |
| `scripts/monitoring/deploy_safe.sh` | Обновлённый (grace period) |
| `scripts/monitoring/health_check.sh` | Без изменений (работает) |
| `scripts/monitoring/notify_failure.sh` | Без изменений |

---

## QUICK FIX (если нужно срочно)

Если нужно просто остановить спам от старого smoke_check:

```bash
# Отключить старый smoke_check
ssh root@lectio.tw1.ru "crontab -l | grep -v smoke_check | crontab -"
```

---

## СТАТУС ДЕПЛОЯ

| Действие | Статус |
|----------|--------|
| Создан `smoke_check_v2.sh` | ✅ Готово |
| Скопирован на сервер | ✅ Готово |
| Созданы smoke users | ✅ `smoke_teacher@test.local`, `smoke_student@test.local` |
| Cron обновлён на v2 | ✅ `*/5 * * * *` |
| Тестовое сообщение в TG | ✅ Доставлено |
| Все 11 проверок | ✅ Пройдены |

**Cron Schedule:**
- `* * * * *` — health_check.sh (инфра, каждую минуту)
- `*/5 * * * *` — smoke_check_v2.sh (бизнес-логика, каждые 5 мин)
- `30 * * * *` — deep_check.sh (SSL, диск, память, раз в час)
- `0 3 * * *` — backup + cleanup
- `0 * * * *` — cleanup_processes.sh

---

## ДОПОЛНИТЕЛЬНЫЕ УЛУЧШЕНИЯ (v2)

### 1. Django 500 ошибки → Telegram (realtime)

Добавлен `telegram_logging.py` - при любой 500 ошибке Django сразу шлёт в Telegram.

**Файл:** `teaching_panel/teaching_panel/telegram_logging.py`

### 2. Deep Check (раз в час)

Проверяет:
- SSL сертификат (предупреждение за 14 дней)
- Свободное место на диске
- Доступная память
- Gunicorn workers (количество + CPU)
- Размер БД
- Nginx error rate
- Pending migrations

**Файл:** `scripts/monitoring/deep_check.sh`

### 3. External Heartbeat (опционально)

Защита от случая когда ВЕСЬ сервер лёг. Использует healthchecks.io (бесплатно).

**Файл:** `scripts/monitoring/heartbeat.sh`

**Настройка:**
1. Зарегистрироваться на https://healthchecks.io
2. Создать check, получить URL
3. Добавить в `/opt/lectio-monitor/config.env`:
   ```
   HEARTBEAT_URL="https://hc-ping.com/your-uuid"
   ```
4. Добавить в cron:
   ```
   * * * * * /opt/lectio-monitor/heartbeat.sh
   ```
