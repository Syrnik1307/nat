# 🤖 Автономная работа с сервером Teaching Panel

**Цель документа**: Полная инструкция для AI-агента по самостоятельной работе с production-сервером без участия пользователя.

---

## 1. SSH Конфигурация и доступ

### 1.1 SSH Alias настроен

**Host alias**: `tp`  
**Конфигурация**: `~/.ssh/config`

```ssh-config
Host tp
    HostName 72.56.81.163
    User root
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
```

**SSH Agent**: Активирован и ключ добавлен
```powershell
# Проверка агента
Get-Service ssh-agent | Select-Object Status
# Должно быть: Running

# Проверка ключей
ssh-add -l
# Должен показать отпечаток id_ed25519
```

### 1.2 Команды без пароля

Все SSH команды выполняются **без запроса пароля** благодаря:
- SSH-ключу в `~/.ssh/id_ed25519`
- Добавленному ключу в ssh-agent
- Alias `tp` в конфиге

**Базовый шаблон команд**:
```powershell
ssh tp "команда на сервере"
scp локальный_файл tp:/удаленный/путь/
scp tp:/удаленный/файл ./локальный/путь/
```

---

## 2. Структура сервера

### 2.1 Основные пути

```
/var/www/teaching_panel/
├── teaching_panel/              # Git репозиторий (основной код)
│   ├── accounts/
│   ├── schedule/
│   ├── teaching_panel/         # Settings, URLs
│   │   ├── settings.py
│   │   └── wsgi.py
│   ├── manage.py
│   ├── db.sqlite3
│   ├── gdrive_token.json       # НЕ в git (секрет)
│   └── ...
├── venv/                        # Python virtual environment
│   └── bin/
│       ├── python3
│       ├── gunicorn
│       ├── celery
│       └── ...
├── staticfiles/                 # Собранные static файлы
└── media/                       # User uploads
```

### 2.2 Systemd сервисы

**Расположение**: `/etc/systemd/system/`

1. **teaching_panel.service** — Django (Gunicorn)
2. **celery_worker.service** — Celery worker
3. **celery_beat.service** — Celery beat scheduler
4. **redis-server.service** — Redis (системный)

**Environment overrides**: `/etc/systemd/system/teaching_panel.service.d/override.conf`

```ini
[Service]
Environment="GDRIVE_RECORDINGS_FOLDER_ID=1X_LJRToNnxM619SX4CXYD5T5Lac-EbmA"
Environment="GDRIVE_TOKEN_FILE=/var/www/teaching_panel/teaching_panel/gdrive_token.json"
```

### 2.3 Логи

```bash
# Django (через systemd)
journalctl -u teaching_panel -n 100 --no-pager

# Celery worker
/var/log/celery/worker.log

# Celery beat
/var/log/celery/beat.log

# Nginx (если используется)
/var/log/nginx/access.log
/var/log/nginx/error.log
```

---

## 3. Стандартный рабочий процесс

### 3.1 Деплой изменений (полный цикл)

```powershell
# 1. Локально: коммит и пуш
cd C:\Users\User\Desktop\nat
git add .
git commit -m "feat: описание изменений"
git push

# 2. На сервере: pull изменений
ssh tp "cd /var/www/teaching_panel/teaching_panel && git pull"

# 3. Применить миграции (если есть)
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py migrate"

# 4. Собрать статику (если изменились static файлы)
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py collectstatic --noinput"

# 5. Перезапустить сервисы
ssh tp "systemctl restart teaching_panel celery_worker celery_beat"

# 6. Проверить статус
ssh tp "systemctl status teaching_panel celery_worker celery_beat --no-pager | grep 'Active:'"

# Ожидаемый результат: все "Active: active (running)"
```

### 3.2 Только backend изменения (без миграций)

```powershell
ssh tp "cd /var/www/teaching_panel/teaching_panel && git pull && systemctl restart teaching_panel"
```

### 3.3 Только Celery задачи

```powershell
ssh tp "cd /var/www/teaching_panel/teaching_panel && git pull && systemctl restart celery_worker celery_beat"
```

---

## 4. Частые операции

### 4.1 Проверка здоровья сервера

```powershell
# Все сервисы одной командой
ssh tp "systemctl status teaching_panel celery_worker celery_beat redis --no-pager | grep -E '(Active:|Loaded:)'"

# Ожидается 4 строки "Active: active (running)"
```

### 4.2 Просмотр логов

```powershell
# Django последние 50 строк
ssh tp "journalctl -u teaching_panel -n 50 --no-pager"

# Celery worker последние 30 строк
ssh tp "tail -30 /var/log/celery/worker.log"

# Ошибки Django за последний час
ssh tp "journalctl -u teaching_panel --since '1 hour ago' --no-pager | grep -i error"
```

### 4.3 Перезапуск сервисов

```powershell
# Все сервисы
ssh tp "systemctl restart teaching_panel celery_worker celery_beat"

# Только Django
ssh tp "systemctl restart teaching_panel"

# Только Celery
ssh tp "systemctl restart celery_worker celery_beat"

# С проверкой статуса после
ssh tp "systemctl restart teaching_panel && sleep 2 && systemctl status teaching_panel --no-pager | head -15"
```

### 4.4 Django shell на сервере

```powershell
# Запуск интерактивного shell
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py shell"

# Выполнение одноразовой команды
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python - << 'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','teaching_panel.settings')
import django
django.setup()
from accounts.models import CustomUser
print(f'Total users: {CustomUser.objects.count()}')
PY"
```

### 4.5 Установка Python пакетов

```powershell
# Добавить пакет в requirements.txt локально
echo "new-package==1.0.0" >> teaching_panel\requirements.txt

# Коммит и пуш
git add teaching_panel/requirements.txt
git commit -m "deps: add new-package"
git push

# Установить на сервере
ssh tp "cd /var/www/teaching_panel/teaching_panel && git pull && source ../venv/bin/activate && pip install -r requirements.txt"

# Перезапустить Django
ssh tp "systemctl restart teaching_panel"
```

---

## 5. Управление файлами

### 5.1 Загрузка файлов на сервер

```powershell
# Один файл
scp C:\local\path\file.py tp:/var/www/teaching_panel/teaching_panel/schedule/

# Директория рекурсивно
scp -r C:\local\directory\* tp:/var/www/teaching_panel/teaching_panel/schedule/management/commands/

# С автоматическим рестартом Django после
scp file.py tp:/tmp/file.py ; ssh tp "mv /tmp/file.py /var/www/teaching_panel/teaching_panel/schedule/ && systemctl restart teaching_panel"
```

### 5.2 Скачивание файлов с сервера

```powershell
# Один файл
scp tp:/var/www/teaching_panel/teaching_panel/db.sqlite3 ./backup/

# Логи
scp tp:/var/log/celery/worker.log ./logs/celery_worker_$(Get-Date -Format "yyyy-MM-dd_HH-mm").log

# База данных (backup)
ssh tp "cd /var/www/teaching_panel/teaching_panel && sqlite3 db.sqlite3 '.backup /tmp/db_backup.sqlite3'"
scp tp:/tmp/db_backup.sqlite3 ./backups/db_$(Get-Date -Format "yyyy-MM-dd").sqlite3
ssh tp "rm /tmp/db_backup.sqlite3"
```

### 5.3 Редактирование конфигов напрямую

```powershell
# Создать backup перед изменением
ssh tp "cp /var/www/teaching_panel/teaching_panel/teaching_panel/settings.py /var/www/teaching_panel/teaching_panel/teaching_panel/settings.py.backup"

# Добавить строку в конец файла
ssh tp "echo 'NEW_SETTING = True' >> /var/www/teaching_panel/teaching_panel/teaching_panel/settings.py"

# Заменить значение (осторожно!)
ssh tp "sed -i 's/DEBUG = True/DEBUG = False/' /var/www/teaching_panel/teaching_panel/teaching_panel/settings.py"

# Перезапустить Django
ssh tp "systemctl restart teaching_panel"
```

---

## 6. Работа с базой данных

### 6.1 Миграции

```powershell
# Создать миграции (обычно локально)
cd teaching_panel
python manage.py makemigrations

# Применить на сервере
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py migrate"

# Проверить состояние миграций
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py showmigrations"
```

### 6.2 Django shell запросы

```powershell
# Подсчет объектов
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py shell -c 'from accounts.models import CustomUser; print(f\"Users: {CustomUser.objects.count()}\")'"

# Создать тестового пользователя
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py shell -c '
from accounts.models import CustomUser
user = CustomUser.objects.create_user(email=\"test@example.com\", password=\"test123\", role=\"teacher\")
print(f\"Created user: {user.id}\")
'"
```

### 6.3 Backup базы данных

```powershell
# Автоматический backup с датой
ssh tp "cd /var/www/teaching_panel/teaching_panel && cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)"

# Скачать backup локально
scp tp:/var/www/teaching_panel/teaching_panel/db.sqlite3 ./backups/production_db_$(Get-Date -Format "yyyy-MM-dd").sqlite3
```

---

## 7. Celery управление

### 7.1 Мониторинг задач

```powershell
# Celery inspect (требует рабочий worker)
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && celery -A teaching_panel inspect active"

# Список зарегистрированных задач
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && celery -A teaching_panel inspect registered"

# Статистика
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && celery -A teaching_panel inspect stats"
```

### 7.2 Ручной запуск задачи

```powershell
# Через Django shell
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python - << 'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','teaching_panel.settings')
import django
django.setup()
from schedule.tasks import cleanup_old_recordings
result = cleanup_old_recordings.delay()
print(f'Task ID: {result.id}')
PY"
```

### 7.3 Очистка очереди

```powershell
# Удалить все pending задачи из Redis
ssh tp "redis-cli -n 0 FLUSHDB"

# Перезапустить worker для чистого старта
ssh tp "systemctl restart celery_worker"
```

---

## 8. Отладка проблем

### 8.1 Django не стартует

```powershell
# 1. Проверить логи
ssh tp "journalctl -u teaching_panel -n 100 --no-pager"

# 2. Попробовать запустить вручную
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && gunicorn teaching_panel.wsgi:application --bind 0.0.0.0:8000"

# 3. Проверить настройки
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py check --deploy"

# 4. Права доступа
ssh tp "ls -la /var/www/teaching_panel/teaching_panel/ | head -20"
```

### 8.2 Celery не работает

```powershell
# 1. Проверить Redis
ssh tp "systemctl status redis --no-pager"
ssh tp "redis-cli ping"  # Должно вернуть PONG

# 2. Логи worker
ssh tp "tail -50 /var/log/celery/worker.log"

# 3. Попробовать запустить вручную
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && celery -A teaching_panel worker --loglevel=debug"
```

### 8.3 Google Drive ошибки

```powershell
# 1. Проверить токен
ssh tp "ls -lh /var/www/teaching_panel/teaching_panel/gdrive_token.json"
ssh tp "cat /var/www/teaching_panel/teaching_panel/gdrive_token.json | python3 -m json.tool | head -10"

# 2. Тестовая загрузка
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py test_gdrive_upload --teacher-id 9"

# 3. Проверить переменные окружения
ssh tp "systemctl show teaching_panel.service | grep GDRIVE"
```

### 8.4 Миграции застряли

```powershell
# Откатить последнюю миграцию
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py migrate <app_name> <previous_migration_number>"

# Fake миграция (опасно! использовать если БД уже в нужном состоянии)
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py migrate <app_name> <migration_number> --fake"
```

---

## 9. Google Drive интеграция

### 9.1 Структура OAuth2 токена

**Файл**: `/var/www/teaching_panel/teaching_panel/gdrive_token.json`

**НЕ коммитить в git!** (добавлен в `.gitignore`)

```json
{
  "token": "ya29.a0AfB_...",
  "refresh_token": "1//0gXXX...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "XXXXX.apps.googleusercontent.com",
  "client_secret": "GOCSPX-XXXXX",
  "scopes": ["https://www.googleapis.com/auth/drive.file"],
  "expiry": "2025-12-02T16:00:00Z"
}
```

### 9.2 Обновление токена

```powershell
# 1. Локально сгенерировать новый токен (если истёк refresh_token)
cd teaching_panel
python test_gdrive_oauth.py

# 2. Загрузить на сервер
scp gdrive_token.json tp:/var/www/teaching_panel/teaching_panel/

# 3. Установить права
ssh tp "chmod 600 /var/www/teaching_panel/teaching_panel/gdrive_token.json"

# 4. Перезапустить Django
ssh tp "systemctl restart teaching_panel"
```

### 9.3 Тестирование загрузки

```powershell
# Management команда
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py test_gdrive_upload --teacher-id 9 --name test.txt"

# Через Django shell
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python - << 'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','teaching_panel.settings')
import django
django.setup()
from schedule.gdrive_utils import get_gdrive_manager
from accounts.models import CustomUser
teacher = CustomUser.objects.filter(role='teacher').first()
mgr = get_gdrive_manager()
print(f'Manager initialized: {mgr is not None}')
print(f'Root folder: {mgr.root_folder_id}')
PY"
```

---

## 10. Systemd сервисы: детальная настройка

### 10.1 Просмотр конфигурации

```powershell
# Показать полную конфигурацию сервиса (с overrides)
ssh tp "systemctl cat teaching_panel.service"

# Проверить environment variables
ssh tp "systemctl show teaching_panel.service | grep Environment"
```

### 10.2 Создание/изменение override

```powershell
# Создать override директорию
ssh tp "mkdir -p /etc/systemd/system/teaching_panel.service.d"

# Загрузить override файл
$overrideContent = @"
[Service]
Environment="NEW_VAR=value"
"@
$overrideContent | ssh tp "cat > /etc/systemd/system/teaching_panel.service.d/override.conf"

# Применить изменения
ssh tp "systemctl daemon-reload && systemctl restart teaching_panel"
```

### 10.3 Редактирование systemd сервиса

```powershell
# Скачать текущий сервис файл
scp tp:/etc/systemd/system/celery_worker.service ./celery_worker.service

# Редактировать локально
# ... изменения ...

# Загрузить обратно
scp ./celery_worker.service tp:/etc/systemd/system/

# Применить
ssh tp "systemctl daemon-reload && systemctl restart celery_worker"
```

---

## 11. Автоматические задачи (примеры скриптов)

### 11.1 Полный деплой одной командой

**Файл**: `quick_deploy.ps1` (локально)

```powershell
# Быстрый деплой без вопросов
param([string]$message = "update")

Write-Host "1. Коммит и пуш..." -ForegroundColor Cyan
git add .
git commit -m $message
git push

Write-Host "2. Деплой на сервер..." -ForegroundColor Cyan
ssh tp "cd /var/www/teaching_panel/teaching_panel && git pull"

Write-Host "3. Миграции..." -ForegroundColor Cyan
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py migrate --noinput"

Write-Host "4. Перезапуск сервисов..." -ForegroundColor Cyan
ssh tp "systemctl restart teaching_panel celery_worker celery_beat"

Write-Host "5. Проверка..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
ssh tp "systemctl status teaching_panel celery_worker celery_beat --no-pager | grep 'Active:'"

Write-Host "✅ Деплой завершен!" -ForegroundColor Green
```

**Использование**:
```powershell
.\quick_deploy.ps1 "feat: add new feature"
```

### 11.2 Резервное копирование

```powershell
# Backup базы и файлов одной командой
$date = Get-Date -Format "yyyy-MM-dd_HH-mm"
$backupDir = ".\backups\$date"

New-Item -ItemType Directory -Path $backupDir -Force

# База данных
scp tp:/var/www/teaching_panel/teaching_panel/db.sqlite3 "$backupDir\db.sqlite3"

# Media файлы (если есть)
# scp -r tp:/var/www/teaching_panel/teaching_panel/media "$backupDir\media"

Write-Host "Backup saved to: $backupDir" -ForegroundColor Green
```

### 11.3 Мониторинг здоровья

```powershell
# health_check.ps1
$services = @("teaching_panel", "celery_worker", "celery_beat", "redis")

foreach ($service in $services) {
    $status = ssh tp "systemctl is-active $service"
    if ($status -eq "active") {
        Write-Host "✅ $service" -ForegroundColor Green
    } else {
        Write-Host "❌ $service ($status)" -ForegroundColor Red
    }
}

# Проверка диска
$diskUsage = ssh tp "df -h /var/www | tail -1 | awk '{print `$5}'"
Write-Host "💾 Disk usage: $diskUsage" -ForegroundColor Yellow
```

---

## 12. Безопасность и best practices

### 12.1 Секреты и credentials

**НЕ коммитить**:
- `gdrive_token.json`
- `client_secrets.json`
- `db.sqlite3` (production)
- `.env` (если используется)

**Проверить .gitignore**:
```bash
gdrive_token.json
client_secrets.json
*.sqlite3
.env
__pycache__/
*.pyc
```

### 12.2 Права доступа к файлам

```powershell
# Токен Google Drive только для root
ssh tp "chmod 600 /var/www/teaching_panel/teaching_panel/gdrive_token.json"

# База данных
ssh tp "chmod 664 /var/www/teaching_panel/teaching_panel/db.sqlite3"

# settings.py
ssh tp "chmod 644 /var/www/teaching_panel/teaching_panel/teaching_panel/settings.py"
```

### 12.3 Проверка перед деплоем

```powershell
# Локально: проверить что код работает
cd teaching_panel
python manage.py check
python manage.py test

# На сервере: проверить production готовность
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py check --deploy"
```

---

## 13. Troubleshooting quick reference

| Проблема | Команда проверки | Решение |
|----------|------------------|---------|
| Django не отвечает | `ssh tp "systemctl status teaching_panel"` | `ssh tp "systemctl restart teaching_panel"` |
| Celery задачи не выполняются | `ssh tp "systemctl status celery_worker"` | `ssh tp "systemctl restart celery_worker"` |
| Redis недоступен | `ssh tp "redis-cli ping"` | `ssh tp "systemctl restart redis"` |
| Google Drive 403 | `ssh tp "cat /var/www/teaching_panel/teaching_panel/gdrive_token.json"` | Обновить токен через `test_gdrive_oauth.py` |
| Миграции не применяются | `ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py showmigrations"` | `ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py migrate"` |
| Нет места на диске | `ssh tp "df -h"` | Очистить старые логи / backup |
| 502 Bad Gateway | `ssh tp "journalctl -u teaching_panel -n 50"` | Проверить gunicorn workers |

---

## 14. Контрольный список перед любым изменением

✅ **Перед деплоем**:
1. Локально проверить `python manage.py check`
2. Закоммитить изменения в git
3. Создать backup БД: `scp tp:/var/www/teaching_panel/teaching_panel/db.sqlite3 ./backup_before_deploy.sqlite3`
4. Проверить текущий статус сервисов: `ssh tp "systemctl status teaching_panel celery_worker celery_beat --no-pager | grep Active"`

✅ **После деплоя**:
1. Проверить что сервисы запустились: `ssh tp "systemctl status teaching_panel --no-pager | head -15"`
2. Проверить логи на ошибки: `ssh tp "journalctl -u teaching_panel -n 20 --no-pager | grep -i error"`
3. Smoke test: `curl http://72.56.81.163:8000/` (должен вернуть 200 или редирект)
4. Проверить Celery: `ssh tp "tail -10 /var/log/celery/worker.log"`

---

## 15. Шпаргалка команд (копируй-вставляй)

```powershell
# === БЫСТРЫЙ ДЕПЛОЙ ===
ssh tp "cd /var/www/teaching_panel/teaching_panel && git pull && systemctl restart teaching_panel"

# === ПОЛНЫЙ ДЕПЛОЙ С МИГРАЦИЯМИ ===
ssh tp "cd /var/www/teaching_panel/teaching_panel && git pull && source ../venv/bin/activate && python manage.py migrate && systemctl restart teaching_panel celery_worker celery_beat"

# === ПРОВЕРКА ВСЕХ СЕРВИСОВ ===
ssh tp "systemctl status teaching_panel celery_worker celery_beat redis --no-pager | grep -E '(Loaded:|Active:)'"

# === ЛОГИ ПОСЛЕДНИЕ 30 СТРОК ===
ssh tp "journalctl -u teaching_panel -n 30 --no-pager"

# === CELERY ЛОГИ ===
ssh tp "tail -30 /var/log/celery/worker.log"

# === DJANGO SHELL ===
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py shell"

# === BACKUP БД ===
scp tp:/var/www/teaching_panel/teaching_panel/db.sqlite3 ./backups/db_$(Get-Date -Format 'yyyy-MM-dd_HH-mm').sqlite3

# === ЗАГРУЗИТЬ ФАЙЛ ===
scp local_file.py tp:/var/www/teaching_panel/teaching_panel/schedule/

# === ТЕСТ GOOGLE DRIVE ===
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py test_gdrive_upload --teacher-id 9"

# === ПЕРЕЗАПУСТИТЬ ВСЁ ===
ssh tp "systemctl restart teaching_panel celery_worker celery_beat && sleep 3 && systemctl status teaching_panel celery_worker celery_beat --no-pager | grep Active"
```

---

## 16. Когда нужна помощь пользователя

**Автономно можно делать**:
- ✅ Деплой кода (git pull)
- ✅ Перезапуск сервисов
- ✅ Просмотр логов
- ✅ Django shell команды
- ✅ Миграции БД
- ✅ Установка pip пакетов
- ✅ Тестирование API
- ✅ Backup БД
- ✅ Загрузка/скачивание файлов

**Требует подтверждения**:
- ⚠️ Изменение systemd сервисов
- ⚠️ Изменение Nginx конфига
- ⚠️ Удаление production БД
- ⚠️ Изменение environment variables (если критичные)
- ⚠️ Обновление Python версии
- ⚠️ Массовое удаление файлов

**Нельзя делать автономно**:
- ❌ Ротация OAuth токенов Google (требует браузер)
- ❌ Настройка DNS / домена
- ❌ Оплата / продление сервера
- ❌ Создание новых пользователей ОС
- ❌ Изменение SSH ключей

---

**Итого**: С этим документом AI-агент может полностью автономно управлять сервером для большинства задач деплоя и отладки, без участия пользователя. При возникновении проблем — следовать разделу Troubleshooting.

**Последнее обновление**: 2 декабря 2025
