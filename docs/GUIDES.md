# Lectio Space - Полное руководство

> Сводная документация по настройке, деплою и работе с платформой.
> Последнее обновление: 2 марта 2026

## Содержание

- [1. Быстрый старт](#1-быстрый-старт)
- [2. Деплой](#2-деплой)
  - [2.1 Автоматический деплой](#21-автоматический-деплой)
  - [2.2 Ручной деплой](#22-ручной-деплой)
  - [2.3 SSH-настройка](#23-ssh-настройка)
  - [2.4 Docker](#24-docker)
  - [2.5 Архитектура окружений](#25-архитектура-окружений)
  - [2.6 Git Workflow](#26-git-workflow)
- [3. Zoom интеграция](#3-zoom-интеграция)
  - [3.1 Zoom Pool](#31-zoom-pool)
  - [3.2 Quick Start (API)](#32-quick-start-api)
  - [3.3 Zoom Webhooks](#33-zoom-webhooks)
- [4. Google Drive](#4-google-drive)
  - [4.1 Настройка Service Account](#41-настройка-service-account)
  - [4.2 Миграция файлов на GDrive](#42-миграция-файлов-на-gdrive)
- [5. Google Meet](#5-google-meet)
- [6. Платежи](#6-платежи)
  - [6.1 YooKassa](#61-yookassa)
  - [6.2 T-Bank (Тинькофф)](#62-t-bank-тинькофф)
  - [6.3 Подписки (активация и управление)](#63-подписки-активация-и-управление)
- [7. Telegram](#7-telegram)
  - [7.1 Основной бот](#71-основной-бот)
  - [7.2 Бот восстановления пароля](#72-бот-восстановления-пароля)
  - [7.3 Бот поддержки](#73-бот-поддержки)
  - [7.4 Алерты мониторинга](#74-алерты-мониторинга)
- [8. Система поддержки](#8-система-поддержки)
- [9. Email и SMS](#9-email-и-sms)
  - [9.1 Email (SMTP)](#91-email-smtp)
  - [9.2 SMS верификация](#92-sms-верификация)
  - [9.3 reCAPTCHA](#93-recaptcha)
- [10. Записи уроков](#10-записи-уроков)
  - [10.1 Архитектура записей](#101-архитектура-записей)
  - [10.2 Квоты хранилища](#102-квоты-хранилища)
- [11. Учебные материалы](#11-учебные-материалы)
- [12. AI-проверка домашних заданий](#12-ai-проверка-домашних-заданий)
- [13. Посещаемость и рейтинг](#13-посещаемость-и-рейтинг)
- [14. Быстрый урок](#14-быстрый-урок)
- [15. Мониторинг и восстановление](#15-мониторинг-и-восстановление)
- [16. Нагрузочное тестирование](#16-нагрузочное-тестирование)
- [17. Масштабирование](#17-масштабирование)
- [18. База данных](#18-база-данных)
- [19. Cosmos DB (опционально)](#19-cosmos-db-опционально)
- [20. Дизайн-система](#20-дизайн-система)
- [21. Аварийные процедуры](#21-аварийные-процедуры)
- [22. API Reference](#22-api-reference)

---

## 1. Быстрый старт

### Backend (Django)

```powershell
cd teaching_panel
..\venv\Scripts\Activate.ps1   # или ..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver      # http://127.0.0.1:8000
```

### Frontend (React)

```powershell
cd frontend
npm install
npm start                       # http://localhost:3000, прокси /api -> Django
```

> Django ДОЛЖЕН быть запущен до тестирования фронтенда, иначе логин вернёт HTML 404 вместо JSON.

### Тестовые данные

```powershell
python manage.py createsuperuser
python manage.py shell -c "from create_sample_data import run; run()"
```

---

## 2. Деплой

### 2.1 Автоматический деплой

**Рекомендуемый способ** - скрипт `auto_deploy.ps1`:

```powershell
.\auto_deploy.ps1
```

11 опций в интерактивном меню: полный деплой, только backend/frontend, миграции БД, перезапуск сервисов, мониторинг логов, обслуживание.

**Быстрый деплой** (без обновления зависимостей):

```powershell
.\deploy_fast.ps1 -SkipDeps        # Только код
.\deploy_fast.ps1 -FrontendOnly    # Только фронтенд
.\deploy_fast.ps1 -BackendOnly     # Только бэкенд
.\deploy_fast.ps1 -SkipMigrations  # Пропустить миграции
```

**Production деплой** (с бэкапом БД):

```powershell
.\deploy_to_production.ps1
# Автоматически создаёт бэкап /tmp/deploy_*.sqlite3
# Требует ввести "MIGRATE" для подтверждения миграций
```

### 2.2 Ручной деплой

**SSH One-liner** (полный деплой):

```bash
ssh tp 'cd /var/www/teaching_panel && sudo git pull origin main && source venv/bin/activate && pip install -r teaching_panel/requirements.txt && cd frontend && npm install && npm run build && cd .. && python teaching_panel/manage.py migrate && python teaching_panel/manage.py collectstatic --noinput && sudo systemctl restart teaching-panel && sudo systemctl restart nginx'
```

**Пошаговый деплой**:

```bash
ssh tp                                    # Подключение (alias в ~/.ssh/config)
cd /var/www/teaching_panel
sudo git pull origin main
source venv/bin/activate
pip install -r teaching_panel/requirements.txt
python teaching_panel/manage.py migrate
python teaching_panel/manage.py collectstatic --noinput
cd frontend && npm run build && cd ..
sudo systemctl restart teaching-panel
sudo systemctl restart nginx
```

**Проверка после деплоя**:

```bash
curl -s https://lectiospace.ru/api/me/ | head
sudo systemctl status teaching-panel
sudo journalctl -u teaching-panel --since "5 min ago" --no-pager
```

**Откат**:

```bash
# Откат кода
sudo git checkout <commit-hash>
sudo systemctl restart teaching-panel

# Откат БД (из бэкапа)
sudo cp /tmp/deploy_YYYYMMDD_HHMMSS.sqlite3 db.sqlite3
sudo chown www-data:www-data db.sqlite3
sudo systemctl restart teaching-panel
```

### 2.3 SSH-настройка

**SSH config** (`~\.ssh\config`):

```
Host tp
    HostName 72.56.81.163
    User root
    IdentityFile ~/.ssh/id_rsa
```

**Копирование ключа** (если ещё не настроен):

```powershell
type $env:USERPROFILE\.ssh\id_rsa.pub | ssh root@72.56.81.163 "cat >> ~/.ssh/authorized_keys"
```

**Проверка**:

```powershell
ssh tp "echo 'SSH works!'"
```

### 2.4 Docker

**Dev** (SQLite + Redis):

```bash
docker compose up --build         # localhost:8080
```

**Production** (PostgreSQL + SSL + Nginx):

```bash
# Настроить .env.production
docker compose -f docker-compose.prod.yml up --build -d

# SSL сертификат
docker compose exec certbot certbot --nginx -d lectiospace.ru

# Масштабирование Celery
docker compose -f docker-compose.prod.yml up --scale celery=4
```

Минимальные ресурсы для 10000 пользователей: 4 GB RAM / 2 vCPU.

### 2.5 Архитектура окружений

Три окружения на одном VPS:

| Окружение | Порт | Ветка | Домен |
|-----------|------|-------|-------|
| PROD RU | 8000 | main | lectiospace.ru |
| STAGE RU | 8001 | staging-russia | lectiospace.online |
| PROD AFRICA | 8002 | main-africa | (планируется) |

Feature flags по рынку: YooKassa (РФ), Mobile Money (Африка), Telegram (РФ), PWA (оба).

### 2.6 Git Workflow

Упрощённый воркфлоу для одного разработчика:

```
main (production)  ←  staging (тестирование)  ←  feature/* (разработка)
```

```powershell
# Деплой на staging
.\deploy_simple.ps1 -Target staging

# Деплой на production (после проверки staging)
.\deploy_simple.ps1 -Target production
```

Hotfix: напрямую в main, затем merge back в staging.

---

## 3. Zoom интеграция

### 3.1 Zoom Pool

Система пула общих Zoom-аккаунтов для учителей.

**Архитектура** (5 компонентов):
1. **Модели**: `ZoomAccount` (is_busy, current_lesson), `Lesson` (zoom_start_url, zoom_account_used)
2. **Атомарный захват**: `select_for_update()` в `start_lesson_view()`
3. **Генерация событий**: `get_lessons_for_calendar()`
4. **Авто-освобождение**: Celery `release_stuck_zoom_accounts` каждые 10 мин
5. **Webhook**: `zoom_webhook_receiver()` при `meeting.ended`

**Настройка** (`.env`):

```bash
ZOOM_ACCOUNT_ID=<account-id>
ZOOM_CLIENT_ID=<client-id>
ZOOM_CLIENT_SECRET=<client-secret>
ZOOM_WEBHOOK_SECRET_TOKEN=<secret-token>
```

**Добавление аккаунтов**: Django Admin -> Zoom Accounts -> Add

**Мониторинг**: `GET /api/schedule/zoom-accounts/` -> занятость аккаунтов

**Troubleshooting**:
- "Все аккаунты заняты" -> `ZoomAccount.objects.all().update(current_meetings=0)`
- 401 от Zoom -> проверить credentials в `.env`
- Аккаунты не освобождаются -> `release_stuck_zoom_accounts.delay()`

### 3.2 Quick Start (API)

**3 способа запуска Zoom-урока**:

```bash
# 1. Через Zoom Pool (рекомендуется)
POST /api/schedule/lessons/{lesson_id}/start-new/

# 2. Быстрый старт (без расписания)
POST /api/schedule/lessons/quick-start/
Body: {title, duration, group_id}

# 3. Персональные credentials учителя
POST /api/schedule/lessons/{lesson_id}/start/
```

Ответ: `zoom_start_url`, `zoom_join_url`, `zoom_meeting_id`, `zoom_password`, `account_email`

OAuth токен кэшируется 50 мин (живёт 60 мин), ключ кэша: `zoom_oauth_token_{account_id}`

### 3.3 Zoom Webhooks

**Настройка** (marketplace.zoom.us -> Server-to-Server OAuth app):
1. Event Subscriptions -> Add
2. URL: `https://lectiospace.ru/schedule/api/zoom/webhook/`
3. Events: `recording.completed`, `recording.trashed`, `recording.deleted`, `meeting.started`, `meeting.ended`
4. Сохранить Secret Token -> `ZOOM_WEBHOOK_SECRET_TOKEN` в `.env`

**Безопасность**: HMAC SHA256 подпись (`x-zm-signature`) + защита от replay attacks (`x-zm-request-timestamp`)

**Поток**: запись Zoom -> webhook -> Celery скачивает -> загрузка в GDrive -> ученики видят в ЛК -> автоудаление через 90 дней

---

## 4. Google Drive

### 4.1 Настройка Service Account

1. console.cloud.google.com -> новый проект -> включить Google Drive API
2. Credentials -> Service Account -> JSON ключ -> `gdrive-credentials.json`
3. Google Drive -> папка "Teaching Panel Recordings" -> поделиться с Service Account email (Editor)
4. Скопировать Folder ID из URL

**На сервере**:

```bash
scp gdrive-credentials.json root@72.56.81.163:/var/www/teaching_panel/
ssh tp 'chmod 600 /var/www/teaching_panel/gdrive-credentials.json && chown www-data:www-data /var/www/teaching_panel/gdrive-credentials.json'
```

**`.env`**:

```bash
GDRIVE_CREDENTIALS_FILE=/var/www/teaching_panel/gdrive-credentials.json
GDRIVE_RECORDINGS_FOLDER_ID=<folder-id>
USE_GDRIVE_STORAGE=1
GDRIVE_ROOT_FOLDER_ID=<id>
GDRIVE_HOMEWORK_FOLDER_ID=<id>
GDRIVE_MATERIALS_FOLDER_ID=<id>
GDRIVE_ATTACHMENTS_FOLDER_ID=<id>
```

`pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`

**Не коммитить** `gdrive-credentials.json`! Ротация ключей каждые 90 дней.

~300 MB/час записи, ~180 GB/месяц -> 2TB хватит на ~1 год. Автоудаление через 90 дней.

### 4.2 Миграция файлов на GDrive

**Структура папок**: TeachingPanel/ -> Recordings/, Homework/, Materials/, Attachments/

```bash
# Бэкап
tar -czf media_backup.tar.gz media/

# Проверка (dry run)
python manage.py migrate_to_gdrive --dry-run

# Миграция
python manage.py migrate_to_gdrive --execute

# Очистка серверного хранилища
rm -rf media/homework_submissions/* media/lesson_materials/*
```

**Откат**: `USE_GDRIVE_STORAGE=0` в `.env` + восстановить из бэкапа.

---

## 5. Google Meet

Feature flag: `GOOGLE_MEET_ENABLED=1`

**Настройка**:
1. Google Cloud Console -> Calendar API -> OAuth 2.0 credentials
2. Redirect URI: `https://lectiospace.ru/api/google-meet/callback/`
3. `.env`: `GOOGLE_MEET_ENABLED=1`, `GOOGLE_MEET_CLIENT_ID`, `GOOGLE_MEET_CLIENT_SECRET`
4. Systemd override для переменных

**Troubleshooting**: `redirect_uri_mismatch` -> проверить URI в GCP Console, `access_denied` -> проверить scopes.

---

## 6. Платежи

### 6.1 YooKassa

**Тарифы**: Месячная 990 руб (30 дней, 5 GB), Годовая 9900 руб (365 дней, 10 GB), Хранилище 20 руб/GB (навсегда).

**Настройка**:
1. Регистрация yookassa.ru -> Account ID + Secret Key
2. Webhook URL: `https://lectiospace.ru/api/payments/yookassa/webhook/`
3. События: `payment.succeeded`, `payment.canceled`

**`.env`**:

```bash
YOOKASSA_ACCOUNT_ID=<id>
YOOKASSA_SECRET_KEY=<key>
YOOKASSA_WEBHOOK_SECRET=<secret>
FRONTEND_URL=https://lectiospace.ru
```

`pip install yookassa>=3.0.0`

**Mock-режим**: Когда `YOOKASSA_ACCOUNT_ID` не установлен -> возвращает mock URLs.

**API**:

```
GET  /api/subscription/                  # Текущая подписка
POST /api/subscription/create-payment/   # {plan: 'monthly'|'yearly'}
POST /api/subscription/add-storage/      # {gb: 50}
POST /api/subscription/cancel/           # Отмена автопродления
POST /api/payments/yookassa/webhook/     # Webhook (автоматический)
```

**Блокировка** при истечении: `@require_active_subscription` -> 403 на: запуск уроков, записи. Не блокируется: профиль, настройки.

**Тестовые карты**: `5555 5555 5555 4444` (успех), `5555 5555 5555 5599` (отказ).

### 6.2 T-Bank (Тинькофф)

Параллельная интеграция с YooKassa.

**`.env`**:

```bash
TBANK_TERMINAL_KEY=<key>
TBANK_SECRET_KEY=<key>
TBANK_PASSWORD=<password>
```

**API**:

```
POST /api/subscription/tbank/create-payment/  # {plan, return_url}
POST /api/subscription/tbank/add-storage/     # {gb}
POST /api/payments/tbank/webhook/             # Webhook
```

Поддерживает рекуррентные платежи через `RebillId`. Webhook верификация: SHA-256 Token.

**Тестовые карты**: `4300 0000 0000 0777` (3DS), `5000 0000 0000 0108` (без 3DS), `2201 3820 0000 0013` (МИР).

### 6.3 Подписки (активация и управление)

**Ручная активация** (management command):

```bash
python manage.py activate_subscription --email teacher@example.com --days 30
python manage.py activate_subscription --telegram-id 123456 --days 365
```

**Django shell**:

```python
from accounts.models import Subscription
sub = Subscription.objects.get(user__email='teacher@example.com')
sub.status = 'active'
sub.expires_at = timezone.now() + timedelta(days=30)
sub.save()
```

**Массовая активация** всех учителей:

```python
from accounts.models import CustomUser, Subscription
for teacher in CustomUser.objects.filter(role='teacher'):
    sub, _ = Subscription.objects.get_or_create(user=teacher)
    sub.status = 'active'
    sub.expires_at = timezone.now() + timedelta(days=365)
    sub.save()
```

**Админский API**: `SubscriptionAdminViewSet` -> extend_trial, cancel, activate.

---

## 7. Telegram

### 7.1 Основной бот

**Создание**: @BotFather -> `/newbot` -> получить токен

**`.env`**: `TELEGRAM_BOT_TOKEN=<token>`

**Запуск**: `python telegram_bot.py`

**Systemd**: `/etc/systemd/system/telegram_bot.service`

**Команды**: `/start`, `/link <код>`, `/unlink`, `/menu`, `/lessons`, `/homework`, `/notifications`, `/help`

### 7.2 Бот восстановления пароля

Пользователь привязывает Telegram ID через настройки на сайте, затем через `/reset` получает ссылку сброса пароля (токен 15 мин).

**API**:

```
POST /accounts/api/password-reset/request-code/    # email + метод
POST /accounts/api/password-reset/verify-code/      # 6-значный код
POST /accounts/api/password-reset/set-password/      # новый пароль (токен 30 мин)
```

### 7.3 Бот поддержки

Двусторонняя связь: админы получают уведомления о тикетах и отвечают прямо из Telegram.

**`.env`**: `SUPPORT_BOT_TOKEN=<token>`

**Запуск**: `python support_bot.py`

**Команды**: `/tickets`, `/view_<id>`, `/reply <id> <текст>`, `/incident <название>`, `/resolve`, `/stats`, `/sla`

**Приоритеты SLA**: P0 (15 мин), P1 (2 ч), P2 (8 ч), P3 (24 ч)

### 7.4 Алерты мониторинга

Настройка группы Telegram для получения алертов: см. [scripts/monitoring/TELEGRAM_GROUP_SETUP.md](../scripts/monitoring/TELEGRAM_GROUP_SETUP.md)

---

## 8. Система поддержки

**Виджет**: фиолетовый круг `?` на всех страницах. Создание тикетов с приоритетами и категориями.

**Статусы**: Новый -> В работе -> Ожидает ответа -> Решён -> Закрыт

**API**:

```
GET  /api/support/tickets/                    # Список тикетов
POST /api/support/tickets/                    # Создать тикет
POST /api/support/tickets/{id}/add_message/   # Добавить сообщение
POST /api/support/tickets/{id}/resolve/       # Решить
POST /api/support/tickets/{id}/reopen/        # Переоткрыть
GET  /api/support/tickets/unread-count/       # Непрочитанные
GET  /api/support/status/                     # Статус системы
GET  /api/support/health/                     # Health check
```

**Категории**: login, payment, lesson, zoom, homework, recording, other

**Django Admin**: SupportTicket, SupportMessage, QuickSupportResponse

---

## 9. Email и SMS

### 9.1 Email (SMTP)

**Gmail** (с App Password):

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<16-символьный-app-password>
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

Альтернативы: Яндекс (`smtp.yandex.ru`), Mail.ru (`smtp.mail.ru`).

### 9.2 SMS верификация

Через SMS.RU: регистрация -> API ID -> пополнение (~1.15 руб/SMS).

**`.env`**: `SMSRU_API_ID=<id>`, `SMSRU_FROM_NAME=Lectio`

**API**:

```
POST /accounts/api/sms/send-code/     # Отправка 6-значного кода
POST /accounts/api/sms/verify-code/   # Проверка (3 попытки)
POST /accounts/api/sms/resend-code/   # Повторная отправка
```

Защита: 1 SMS/мин, 3 попытки, TTL 10 мин.

### 9.3 reCAPTCHA

Google reCAPTCHA v3 (невидимая, score 0.0-1.0).

**`.env`**:

```bash
RECAPTCHA_PUBLIC_KEY=<site-key>
RECAPTCHA_PRIVATE_KEY=<secret-key>
RECAPTCHA_REQUIRED_SCORE=0.5
RECAPTCHA_ENABLED=true    # false для dev
```

`pip install django-recaptcha`

Frontend: хук `useRecaptcha` -> `executeRecaptcha('register')`.

---

## 10. Записи уроков

### 10.1 Архитектура записей

**Поток**: Zoom запись -> webhook `recording.completed` -> Celery task -> скачивание -> загрузка в GDrive -> `LessonRecording` в БД -> доступ ученикам -> автоудаление через 90 дней.

**Модели**: `LessonRecording` (lesson, gdrive_file_id, file_size_bytes, duration_seconds, is_available)

**API (учитель)**: `GET /api/schedule/recordings/teacher/` - список записей, управление доступом

**API (ученик)**: `GET /api/schedule/recordings/` - доступные записи

**Настройка**:
- `pip install google-auth google-api-python-client`
- GDrive credentials + Zoom webhook (см. разделы 3.3 и 4.1)
- Celery для фоновой загрузки

### 10.2 Квоты хранилища

**Модель**: `TeacherStorageQuota` - total_quota_bytes (5 GB default), used_bytes, recordings_count, purchased_gb

**Предупреждения**: 80% -> warning, 90% -> оранжевый, >90% -> красный

**API (admin)**:

```
GET  /schedule/api/storage/quotas/          # Все квоты
GET  /schedule/api/storage/quotas/<id>/     # Конкретная квота
POST /schedule/api/storage/quotas/<id>/increase/        # Увеличить
POST /schedule/api/storage/quotas/<id>/reset-warnings/  # Сбросить
GET  /schedule/api/storage/statistics/      # Общая статистика
```

**UI**: `/admin/storage` - карточки статистики, прогресс-бары, управление квотами.

---

## 11. Учебные материалы

Загрузка теории и конспектов (ссылки на GDrive), трекинг просмотров.

**Модели**: `LessonMaterial` (lesson, title, material_type, gdrive_file_id), `MaterialView` (material, student, viewed_at)

**Компоненты**: `LessonMaterialsManager` (учитель), `LessonMaterialsViewer` (ученик)

Статистика: кто прочитал, процент завершения.

---

## 12. AI-проверка домашних заданий

**Провайдеры**: DeepSeek ($0.001/запрос), OpenAI GPT-4o-mini

**Настройка** (поля на задании): `ai_grading_enabled`, `ai_provider`, `ai_grading_prompt`

**Логика**: confidence < 70% -> ручная проверка учителем

**AI-отчёты**: strengths, weaknesses, common_mistakes, recommendations, progress_trend

---

## 13. Посещаемость и рейтинг

**Модели**: `AttendanceRecord`, `UserRating`, `IndividualStudent`

**Рейтинговая система**:
- +10 баллов: посещение урока
- +10 баллов: просмотр записи
- -5 баллов: отсутствие
- +5 баллов: выполнение ДЗ (планируется)
- +15/+8 баллов: контрольные точки (планируется)

**API**:

```
POST /api/schedule/lessons/{id}/attendance/auto_record/    # Автозапись
POST /api/schedule/lessons/{id}/attendance/manual_record/   # Ручная запись
GET  /api/schedule/groups/{id}/rating/                      # Рейтинг группы
```

---

## 14. Быстрый урок

Мгновенный запуск Zoom без создания урока в расписании.

```
POST /api/schedule/lessons/quick-start/
Body: {title, duration, group_id, record: true/false, privacy: "all"|"groups"|"students", ...}
```

Опции записи с настройками приватности: все ученики / выбранные группы / выбранные ученики.

---

## 15. Мониторинг и восстановление

**Компоненты**:
- `health_check.sh` - cron каждую минуту
- Systemd watchdog (60 сек)
- Telegram алерты (CRITICAL/WARNING/INFO)
- `deploy_safe.sh` - авто-rollback при ошибке

**SLA**: сервис упал -> 5 сек recovery, плохой деплой -> 30 сек rollback.

**Установка**: `bash install_monitoring.sh`

---

## 16. Нагрузочное тестирование

Locust: тестовые данные (1002 учителя, 3003 ученика, 500 ДЗ).

```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 --run-time 5m --csv=results
```

**Целевые KPI**: P95 < 500ms, Failure Rate < 1%.

---

## 17. Масштабирование

| Stage | Учителей | RAM | vCPU | Стоимость |
|-------|----------|-----|------|-----------|
| A (MVP) | 300 | 4 GB | 2 | ~$24/мес |
| B (Growth) | 750 | 8 GB | 4 | ~$100/мес |
| C (Scale) | 1500 | 16 GB | 8 | ~$500/мес |

Stage B: PgBouncer, CDN для статики. Stage C: Load balancer, read replica.

Готовые конфигурации: [deploy/scaling/README.md](../deploy/scaling/README.md)

---

## 18. База данных

### Миграция SQLite -> PostgreSQL

```bash
# 1. Установить PostgreSQL
sudo apt install postgresql postgresql-contrib

# 2. Создать БД
sudo -u postgres createdb teaching_panel
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '$(openssl rand -base64 32)';"

# 3. Бэкап SQLite
cp db.sqlite3 db.sqlite3.backup
python manage.py dumpdata > backup.json

# 4. Pip install
pip install psycopg2-binary redis django-redis

# 5. .env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/teaching_panel

# 6. Миграция
python manage.py migrate
python manage.py loaddata backup.json

# 7. Проверка
python manage.py dbshell
```

**Откат**: удалить `DATABASE_URL`, восстановить SQLite из бэкапа.

---

## 19. Cosmos DB (опционально)

Feature flag: `COSMOS_DB_ENABLED=1`

**Эмулятор** (для локальной разработки):

```bash
# Windows
winget install Microsoft.AzureCosmosDBEmulator

# Docker
docker run -p 8081:8081 -p 10251-10254:10251-10254 mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator
```

**`.env.local`**: `COSMOS_DB_URL=https://localhost:8081/`, `COSMOS_DB_KEY=<emulator-key>`

**Миграция**: `python manage.py shell -c "import manage_cosmos_migration as m; m.run()"`

---

## 20. Дизайн-система

**Цвета**:

| Назначение | Цвет | HEX |
|------------|------|-----|
| Primary | Indigo | #4F46E5 |
| Primary hover | Indigo Dark | #4338CA |
| Success | Emerald | #10B981 |
| Error | Rose | #F43F5E |
| Warning | Amber | #F59E0B |
| Background | Slate 50 | #F8FAFC |
| Text | Slate 900 | #0F172A |

**Шрифт**: Plus Jakarta Sans (Inter fallback)

**CSS токены** (из `smooth-transitions.css`):

```css
--duration-instant: 100ms;   /* Мгновенные */
--duration-fast: 180ms;      /* Hover, click */
--duration-normal: 280ms;    /* Переключения */
--duration-slow: 400ms;      /* Модалки */
--ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
```

**Правила**: никогда `display: none -> block` без анимации, все интерактивные элементы = transition, skeleton loaders вместо пустоты. Подробнее: [FRONTEND_SMOOTHNESS_RULES.md](../FRONTEND_SMOOTHNESS_RULES.md)

**Shared Components**: `Button`, `Input`, `Modal`, `Card`, `Badge` из `frontend/src/shared/components/`

---

## 21. Аварийные процедуры

### Восстановление изображений ДЗ

```bash
# Диагностика
python diagnose_and_restore_hw_images.py --diagnose

# Восстановление (с dry run)
python diagnose_and_restore_hw_images.py --restore --dry-run
python diagnose_and_restore_hw_images.py --restore --backup
```

Типы проблем: `GDRIVE_FILE_MISSING`, `LOCAL_FILE_MISSING`. Можно восстановить из корзины GDrive (30 дней).

### Восстановление БД

```bash
# Бэкап
ssh tp 'cd /var/www/teaching_panel && sudo cp db.sqlite3 /tmp/backup_$(date +%Y%m%d_%H%M%S).sqlite3'

# Проверка
ssh tp 'sqlite3 /tmp/backup_*.sqlite3 "PRAGMA integrity_check;"'  # должен вернуть "ok"

# Восстановление
ssh tp 'cd /var/www/teaching_panel && sudo cp /tmp/deploy_YYYYMMDD_HHMMSS.sqlite3 db.sqlite3 && sudo chown www-data:www-data db.sqlite3 && sudo systemctl restart teaching-panel'
```

### Все сервисы упали

```bash
ssh tp
sudo systemctl restart teaching-panel
sudo systemctl restart nginx
sudo systemctl status teaching-panel nginx
sudo journalctl -u teaching-panel --since "10 min ago" --no-pager
```

---

## 22. API Reference

### Аутентификация (JWT)

```
POST /api/jwt/token/      # Логин {email, password} -> {access, refresh}
POST /api/jwt/refresh/    # Обновить {refresh} -> {access}
POST /api/jwt/register/   # Регистрация {email, password, role} -> {access, refresh}
```

JWT payload содержит `role` (student/teacher/admin).

### Расписание и Уроки

```
GET    /api/schedule/lessons/              # Список уроков
POST   /api/schedule/lessons/              # Создать урок
POST   /api/schedule/lessons/{id}/start-new/     # Запустить через Zoom Pool
POST   /api/schedule/lessons/quick-start/         # Быстрый урок
GET    /api/schedule/groups/               # Группы
GET    /api/schedule/zoom-accounts/        # Статус Zoom-аккаунтов
```

### Домашние задания

```
GET    /api/homework/assignments/          # Список заданий
POST   /api/homework/assignments/          # Создать задание
GET    /api/homework/submissions/          # Список сдач
POST   /api/homework/submissions/          # Сдать задание
POST   /api/homework/submissions/{id}/grade/  # Оценить
```

### Записи

```
GET    /api/schedule/recordings/           # Записи (ученик)
GET    /api/schedule/recordings/teacher/   # Записи (учитель)
DELETE /api/schedule/recordings/{id}/      # Удалить запись
```

### Подписки

```
GET    /api/subscription/                        # Текущая подписка
POST   /api/subscription/create-payment/         # Создать платёж
POST   /api/subscription/add-storage/            # Докупить хранилище
POST   /api/subscription/cancel/                 # Отменить
POST   /api/payments/yookassa/webhook/           # YooKassa webhook
POST   /api/payments/tbank/webhook/              # T-Bank webhook
```

### Поддержка

```
GET    /api/support/tickets/                     # Тикеты
POST   /api/support/tickets/                     # Создать тикет
POST   /api/support/tickets/{id}/add_message/    # Сообщение
POST   /api/support/tickets/{id}/resolve/        # Решить
GET    /api/support/status/                      # Статус системы
```

### Пользователь

```
GET    /api/me/                                  # Текущий пользователь
PUT    /api/me/                                  # Обновить профиль
GET    /api/accounts/teachers/                   # Список учителей (admin)
```
