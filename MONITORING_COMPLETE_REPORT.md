# Отчёт: Полная система мониторинга Lectio

## Обзор

Реализована комплексная система мониторинга, покрывающая все аспекты работы платформы.

## Созданные компоненты

### 1. Smoke-тесты бизнес-логики (`smoke_check_v2.sh`)

| # | Проверка | Описание |
|---|----------|----------|
| 1 | Static files | Доступность CSS/JS |
| 2 | Health + DB | Эндпоинт /health-check/ |
| 3 | Teacher JWT | Авторизация учителя |
| 4 | Lessons API | Список уроков |
| 5 | Recordings API | Список записей |
| 6 | Homework API | Домашние задания |
| 7 | Subscription | Статус подписки |
| 8 | Payments | Платёжные методы |
| 9 | Groups API | Группы учеников |
| 10 | Student JWT | Авторизация ученика |
| 11 | Student homework | ДЗ для ученика |

**Расписание:** каждые 5 минут

### 2. Глубокие проверки (`deep_check.sh`)

- SSL сертификат (предупреждение за 14 дней до истечения)
- Свободное место на диске (warn: 20%, crit: 10%)
- Оперативная память (warn: 500MB, crit: 200MB)
- Воркеры Gunicorn (минимум 3)
- Ошибки Nginx (500/502/503)
- Незапущенные миграции

**Расписание:** каждый час

### 3. Проверка интеграций (`integration_check.sh`)

- Google Drive API (создание/удаление тестового файла)
- Zoom OAuth (получение токена)
- T-Bank API (доступность)
- YooKassa API (доступность)
- Telegram Bot API (getMe)

**Расписание:** каждые 6 часов

### 4. Мониторинг latency (`latency_check.sh`)

| Порог | Статус |
|-------|--------|
| < 2s | OK |
| 2-5s | WARNING |
| > 5s | CRITICAL |

Проверяемые эндпоинты:
- /health-check/
- /api/me/
- /api/schedule/lessons/
- /static/

**Расписание:** каждые 5 минут (вместе со smoke)

### 5. Детекция атак (`security_check.sh`)

- Brute-force: >50 ответов 401/403 за 15 минут
- SQL injection: попытки в логах
- Path traversal: `../` в запросах
- Сканеры: nikto, sqlmap, nmap, acunetix
- DDoS: >1000 запросов за минуту

**Расписание:** каждые 15 минут

### 6. Prometheus метрики (`prometheus_metrics.py`)

Эндпоинт: `/metrics/`

Метрики:
- `http_requests_total`
- `http_request_duration_seconds`
- `app_active_users_24h`
- `app_total_users`
- `db_connection_healthy`
- `cache_connection_healthy`
- `app_lessons_today`
- `app_total_recordings`
- `app_active_subscriptions`

### 7. Django 500 → Telegram (`telegram_logging.py`)

Автоматическая отправка всех HTTP 500 ошибок в Telegram с:
- Traceback
- URL и метод запроса
- User-Agent
- User ID (если авторизован)
- Антиспам: 5 минут между одинаковыми ошибками

### 8. Sentry интеграция (`sentry_config.py`)

- Автоматический сбор всех exceptions
- Performance monitoring (10% транзакций)
- Группировка ошибок
- Фильтрация PII

**Требуется:** добавить `SENTRY_DSN` в `.env`

## Структура файлов

```
scripts/monitoring/
├── smoke_check_v2.sh        # 11 бизнес-проверок
├── deep_check.sh            # SSL, диск, память, воркеры
├── integration_check.sh     # GDrive, Zoom, платежи
├── latency_check.sh         # Время ответа
├── security_check.sh        # Детекция атак
├── heartbeat.sh             # Внешний uptime
├── setup_smoke_users.sh     # Создание тест-аккаунтов
├── deploy_monitoring.sh     # Деплой всего на сервер
├── notify_failure.sh        # Отправка в Telegram
├── deploy_safe.sh           # Безопасный деплой
├── TELEGRAM_GROUP_SETUP.md  # Инструкция по группе
└── config.env               # (на сервере)

teaching_panel/teaching_panel/
├── telegram_logging.py      # Django 500 → Telegram
├── prometheus_metrics.py    # /metrics/ эндпоинт
└── sentry_config.py         # Sentry SDK
```

## Cron расписание

```
* * * * *      health_check.sh       # Базовое здоровье
*/5 * * * *    smoke_check_v2.sh     # Бизнес-логика
30 * * * *     deep_check.sh         # Инфраструктура
0 */6 * * *    integration_check.sh  # API интеграций
*/15 * * * *   security_check.sh     # Безопасность
*/5 * * * *    heartbeat.sh          # Внешний uptime
```

## Деплой

```bash
# Из папки scripts/monitoring/
chmod +x deploy_monitoring.sh
./deploy_monitoring.sh
```

Или вручную:

```bash
scp *.sh root@lectio.tw1.ru:/opt/lectio-monitor/
ssh root@lectio.tw1.ru "chmod +x /opt/lectio-monitor/*.sh"
```

## Следующие шаги

1. **Healthchecks.io** - создать проект и добавить URL в `heartbeat.sh`
2. **Sentry** - создать проект, добавить DSN в `.env`
3. **Telegram группа** - создать по инструкции `TELEGRAM_GROUP_SETUP.md`
4. **Grafana** (опционально) - подключить к `/metrics/` для дашбордов

## Антиспам

Все скрипты имеют защиту от флуда:
- Одинаковый алерт повторяется не чаще раза в 5 минут
- Во время деплоя алерты отключаются (файл-маркер)
- Heartbeat не алертит при первом запуске

## Логи

```bash
# Смотреть все логи
ssh root@lectio.tw1.ru "tail -f /var/log/lectio-monitor/*.log"

# Только ошибки
ssh root@lectio.tw1.ru "grep -h FAIL /var/log/lectio-monitor/*.log"
```

---

**Создано:** $(date)
**Версия:** 2.0
