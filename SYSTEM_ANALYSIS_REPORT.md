# 📊 ПОЛНЫЙ АНАЛИЗ СИСТЕМЫ Teaching Panel

**Дата**: 29 ноября 2025  
**Тип**: Комплексный аудит безопасности, производительности и архитектуры

---

## 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ (требуют немедленного действия)

### 1. DEBUG=True в продакшене
**Риск**: КРИТИЧЕСКИЙ 🔴  
**Статус**: Django `check --deploy` показал `security.W018`

**Проблема**:
```python
# settings.py:39
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')
```
По умолчанию DEBUG включен! В продакшене это:
- Раскрывает структуру БД в ошибках
- Показывает SECRET_KEY в трейсбеках
- Выдаёт полные пути к файлам
- Замедляет работу (хранит все SQL запросы в памяти)

**Решение**:
```bash
# На сервере
echo "DEBUG=False" >> /etc/environment
# ИЛИ в systemd service:
Environment="DEBUG=False"
```

---

### 2. Дефолтный SECRET_KEY
**Риск**: КРИТИЧЕСКИЙ 🔴  
**Статус**: `security.W009` - использует django-insecure ключ

**Проблема**:
```python
# settings.py:28
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-change-this-in-production')
```

Если `SECRET_KEY` не задан в окружении, используется дефолтный! Это:
- Позволяет подделывать JWT токены
- Компрометирует сессии пользователей
- Делает CSRF защиту бесполезной

**Решение** (выполнить СРОЧНО):
```bash
# Генерация нового ключа
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Установка на сервере
echo "SECRET_KEY='<сгенерированный_ключ>'" >> /etc/environment

# Перезапуск
systemctl restart teaching_panel
```

---

### 3. Zoom API credentials хранятся в plaintext
**Риск**: ВЫСОКИЙ 🟠  
**Проблема**: В модели `ZoomAccount`:
```python
api_key = models.CharField(max_length=255)      # plaintext!
api_secret = models.CharField(max_length=255)   # plaintext!
```

Все Zoom API ключи доступны через:
- Django Admin (любой staff может увидеть)
- API endpoint `/api/zoom-pool/` (если утечёт токен)
- Прямой доступ к БД

**Решение**:
1. Использовать `django-encrypted-model-fields` или `cryptography`
2. Шифровать через Fernet symmetric encryption
3. Ключ шифрования хранить в `SECRET_KEY` или отдельном `FIELD_ENCRYPTION_KEY`

**Пример**:
```python
from encrypted_model_fields.fields import EncryptedCharField

class ZoomAccount(models.Model):
    api_key = EncryptedCharField(max_length=255)
    api_secret = EncryptedCharField(max_length=255)
```

---

### 4. Нет HTTPS/SSL
**Риск**: ВЫСОКИЙ 🟠  
**Статус**: `security.W004`, `W008`, `W012`, `W016`

**Проблемы**:
```python
SECURE_SSL_REDIRECT = False        # security.W008
SESSION_COOKIE_SECURE = False      # security.W012
CSRF_COOKIE_SECURE = False         # security.W016
SECURE_HSTS_SECONDS = 0            # security.W004
```

Текущее состояние:
- Весь трафик HTTP (не зашифрован)
- Пароли передаются открытым текстом
- JWT токены могут быть перехвачены
- Man-in-the-middle атаки возможны

**Решение**:
1. Установить Let's Encrypt сертификат
2. Настроить nginx для HTTPS
3. Обновить `settings.py`:
```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 год
CSRF_TRUSTED_ORIGINS = ['https://teachingpanel.com']
```

---

### 5. SQLite в продакшене
**Риск**: СРЕДНИЙ 🟡  
**Проблема**: SQLite не предназначен для production с конкурентной записью

**Текущие ограничения**:
- Только 1 writer одновременно (блокирует всю БД)
- Нет репликации
- При росте >100MB начнутся проблемы с производительностью
- Текущий размер: 756KB (пока нормально)

**Наблюдаемые риски**:
- При 50+ одновременных пользователях начнутся тайм-ауты
- Celery задачи могут блокировать API запросы
- База данных может корраптиться при аварийном отключении

**Решение** (среднесрочное):
Миграция на PostgreSQL:
```bash
# Установка PostgreSQL
apt install postgresql postgresql-contrib

# Создание БД
sudo -u postgres createdb teaching_panel
sudo -u postgres createuser teaching_panel_user

# Миграция данных
python manage.py dumpdata > backup.json
# Обновить DATABASE_URL в .env
python manage.py migrate
python manage.py loaddata backup.json
```

---

## 🟡 ВАЖНЫЕ ПРОБЛЕМЫ (исправить в ближайшее время)

### 6. Отсутствие rate limiting на критичных endpoints
**Риск**: СРЕДНИЙ 🟡

**Проблема**: Нет защиты от brute-force атак на:
- `/api/jwt/token/` (логин)
- `/api/jwt/register/` (регистрация)
- `/api/password-reset/` (восстановление пароля)

**Текущая защита**:
```python
# settings.py - есть базовый throttling
'DEFAULT_THROTTLE_RATES': {
    'anon': '100/hour',
    'user': '1000/hour',
    'login': '5/minute',  # ✅ Есть
}
```

**Проблемы**:
- Rate limit по IP, а не по username (можно менять IP)
- Нет блокировки после N неудачных попыток
- Нет капчи после 3 попыток

**Решение**:
1. Добавить `django-ratelimit` с блокировкой по email
2. Интегрировать reCAPTCHA после 3 неудачных логинов
3. Логировать подозрительную активность

---

### 7. Нет логирования изменений ролей
**Риск**: СРЕДНИЙ 🟡

**Проблема**: Когда роль пользователя меняется, нет:
- Записи кто изменил
- Записи старого значения
- Временной метки
- Причины изменения

**Решение** (уже описано в SECURITY_AUDIT_DATABASE.md):
```python
# accounts/admin.py
class CustomUserAdmin(BaseUserAdmin):
    def save_model(self, request, obj, form, change):
        if change and 'role' in form.changed_data:
            old_role = CustomUser.objects.get(pk=obj.pk).role
            logger.warning(
                f"ROLE CHANGE: User {obj.email} (ID:{obj.id}) "
                f"role changed from '{old_role}' to '{obj.role}' "
                f"by {request.user.email}"
            )
        super().save_model(request, obj, form, change)
```

---

### 8. TODO комментарии в production коде
**Риск**: НИЗКИЙ 🟢

Найдены незавершённые функции:
```python
# schedule/views.py:908
# TODO: Verify webhook signature for production

# schedule/tasks.py:130
# TODO: Реализовать отправку email/push уведомлений

# schedule/tasks.py:198
# TODO: Реализация загрузки в S3/Azure

# schedule/tasks.py:604
# TODO: Интегрировать с системой уведомлений
```

**Критичный TODO**:
```python
# schedule/views.py:908
# TODO: Verify webhook signature for production
```

Zoom webhooks НЕ проверяют подпись! Любой может отправить поддельный webhook.

**Решение**:
```python
import hmac
import hashlib

def verify_zoom_webhook(request):
    signature = request.headers.get('x-zm-signature')
    timestamp = request.headers.get('x-zm-request-timestamp')
    
    message = f"v0:{timestamp}:{request.body.decode()}"
    hash_for_verify = hmac.new(
        ZOOM_WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(f"v0={hash_for_verify}", signature):
        raise PermissionDenied("Invalid webhook signature")
```

---

### 9. Устаревшие зависимости
**Риск**: НИЗКИЙ 🟢

```
google-api-python-client 2.110.0 → 2.187.0
google-auth 2.25.2 → 2.43.0
google-auth-oauthlib 1.2.0 → 1.2.3
```

**Решение**:
```bash
pip install --upgrade google-api-python-client google-auth google-auth-oauthlib
```

---

### 10. Нет мониторинга и alerting
**Риск**: СРЕДНИЙ 🟡

**Отсутствует**:
- Мониторинг размера БД
- Alerts на ошибки Django
- Мониторинг Gunicorn workers (могут умереть)
- Alerts на failed backups
- Monitoring использования памяти

**Решение**:
```bash
# Простое решение: healthchecks.io
curl -fsS -m 10 --retry 5 -o /dev/null https://hc-ping.com/YOUR-UUID

# Или настроить Prometheus + Grafana
```

---

## 🟢 АРХИТЕКТУРНЫЕ УЛУЧШЕНИЯ (рекомендации)

### 11. Celery всё ещё в зависимостях
**Статус**: requirements.txt содержит Celery, но не используется

**Найдено**:
```
celery>=5.3.0
redis>=5.0.0
django-celery-beat>=2.8.0
```

Но все Celery задачи удалены из кода. Redis используется, но не для Celery.

**Решение**:
- Удалить `celery` и `django-celery-beat` из requirements.txt
- Оставить `redis` (может использоваться для кеша)
- Удалить `CELERY_*` настройки из settings.py

---

### 12. Отсутствие индексов на часто запрашиваемых полях
**Риск**: Производительность 🟡

**Проблема**: Медленные запросы при росте данных:
```python
# Нет индекса на:
CustomUser.role           # WHERE role='teacher' - очень частый запрос
Lesson.start_time        # ORDER BY start_time
Lesson.teacher_id        # JOIN на учителя
Group.invite_code        # WHERE invite_code='ABC123'
```

**Решение**:
```python
class Meta:
    indexes = [
        models.Index(fields=['role']),
        models.Index(fields=['start_time']),
        models.Index(fields=['teacher', 'start_time']),
    ]
```

---

### 13. N+1 запросы в API
**Риск**: Производительность 🟡

**Возможные места** (нужна проверка через django-debug-toolbar):
```python
# Вероятно в schedule/views.py
lessons = Lesson.objects.all()  # 1 запрос
for lesson in lessons:
    teacher = lesson.teacher  # N запросов!
```

**Решение**:
```python
lessons = Lesson.objects.select_related('teacher', 'group').all()
# ИЛИ
lessons = Lesson.objects.prefetch_related('students').all()
```

---

### 14. Отсутствие кеширования
**Риск**: Производительность 🟡

**Что можно кешировать**:
- Список групп учителя (меняется редко)
- Настройки системы (SystemSettings)
- Статистика dashboard
- Список доступных Zoom аккаунтов

**Решение**:
```python
from django.core.cache import cache

@cached_property
def available_zoom_accounts(self):
    return cache.get_or_set(
        'available_zoom_accounts',
        lambda: ZoomAccount.objects.filter(is_active=True, current_meetings=0),
        timeout=60  # 1 минута
    )
```

---

### 15. Нет CORS для production домена
**Риск**: НИЗКИЙ 🟢

**Проблема**:
```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
```

Если фронтенд на другом домене (например `https://teachingpanel.com`), CORS заблокирует запросы.

**Решение**:
```python
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
```

---

## 📋 ПРИОРИТИЗИРОВАННЫЙ ПЛАН ДЕЙСТВИЙ

### Немедленно (сегодня):
1. ✅ **Создать SECRET_KEY** и установить на сервере
2. ✅ **Отключить DEBUG** в production
3. ✅ **Включить SESSION_COOKIE_SECURE** (хотя бы на уровне nginx)
4. ⏳ Добавить проверку Zoom webhook подписи
5. ⏳ Добавить логирование изменений ролей

### На этой неделе:
6. ⏳ Настроить HTTPS с Let's Encrypt
7. ⏳ Зашифровать Zoom credentials в БД
8. ⏳ Удалить Celery из зависимостей
9. ⏳ Обновить устаревшие пакеты
10. ⏳ Добавить индексы на role и start_time

### На следующей неделе:
11. ⏳ Настроить мониторинг (healthchecks.io или Prometheus)
12. ⏳ Реализовать rate limiting по email
13. ⏳ Добавить django-debug-toolbar для проверки N+1
14. ⏳ Внедрить кеширование часто используемых данных
15. ⏳ Настроить offsite бэкапы (S3/Azure)

### Среднесрочно (месяц):
16. ⏳ Миграция на PostgreSQL
17. ⏳ Настроить репликацию БД
18. ⏳ Внедрить centralized logging (ELK/Loki)
19. ⏳ CI/CD с автоматическими тестами
20. ⏳ Load testing для определения bottlenecks

---

## 🔧 КОМАНДЫ ДЛЯ БЫСТРОГО ИСПРАВЛЕНИЯ

### 1. Генерация SECRET_KEY:
```bash
ssh root@72.56.81.163
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Скопировать вывод
echo "export SECRET_KEY='<вывод>'" >> /etc/environment
systemctl restart teaching_panel
```

### 2. Отключение DEBUG:
```bash
echo "export DEBUG=False" >> /etc/environment
systemctl restart teaching_panel
```

### 3. Проверка применения:
```bash
cd /var/www/teaching_panel && source venv/bin/activate && cd teaching_panel
python manage.py check --deploy
```

### 4. Установка sqlite3 (для лучших бэкапов):
```bash
apt install sqlite3
# Обновить backup_db.sh уже готов к использованию sqlite3
```

### 5. Настройка HTTPS (Let's Encrypt):
```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d teachingpanel.com -d www.teachingpanel.com
# Автоматически обновит nginx конфиг
```

---

## 📊 МЕТРИКИ СИСТЕМЫ (текущее состояние)

**Сервер**:
- CPU: load average 0.11 (отличное)
- RAM: 1.9GB total, 592MB used, 1.3GB available ✅
- Disk: 29GB total, 8.3GB used (29% use) ✅
- Swap: 0B (НЕТ SWAP - может быть проблемой при нехватке RAM)
- Uptime: 19 дней ✅

**База данных**:
- Размер: 756KB (очень мало, всё ок) ✅
- Тип: SQLite ⚠️
- Владелец: www-data:www-data ✅
- Права: 664 ✅
- Backup: Настроен ✅

**Django**:
- Workers: 3 Gunicorn workers ✅
- Status: active (running) ✅
- Warnings: DEBUG=True, SECRET_KEY, HTTPS ❌

**Бэкапы**:
- Расположение: /var/backups/teaching_panel/ ✅
- Последний: db_backup_20251129_194815.sqlite3.gz (24KB) ✅
- Автоматизация: cron 3:00 daily ✅
- Retention: 30 дней ✅

---

## 🎯 РЕЗЮМЕ

**Общая оценка безопасности**: 🟡 СРЕДНЯЯ (требуется улучшение)

**Топ-3 критичные проблемы**:
1. 🔴 DEBUG=True + дефолтный SECRET_KEY
2. 🔴 Нет HTTPS (пароли в открытом виде)
3. 🟠 Zoom credentials в plaintext

**Сильные стороны**:
- ✅ Резервное копирование настроено
- ✅ Права на БД исправлены
- ✅ JWT роли исправлены
- ✅ Rate limiting базовый есть
- ✅ Сервер стабилен (19 дней uptime)

**Следующий шаг**: Запустить команды из раздела "КОМАНДЫ ДЛЯ БЫСТРОГО ИСПРАВЛЕНИЯ" (пункты 1-2).

---

**Статус**: 🟡 ТРЕБУЕТСЯ ДЕЙСТВИЕ  
**Ответственный**: DevOps + Security Team  
**Дата следующей проверки**: 6 декабря 2025
