# 🔔 Настройка Zoom Webhooks для автоматической обработки записей

## 📋 Обзор

Zoom webhooks позволяют автоматически получать уведомления когда:
- ✅ Запись урока готова для скачивания
- ✅ Запись удалена
- ✅ Встреча начата/завершена

Наша система использует это для **полностью автоматической** обработки записей без ручной работы!

---

## 🔧 Шаг 1: Создание Zoom Webhook Subscription

### 1.1 Перейдите в Zoom Marketplace
👉 https://marketplace.zoom.us/

Войдите с аккаунтом администратора Zoom.

### 1.2 Откройте ваше приложение
1. "Manage" → "Build App"
2. Найдите ваше приложение (Server-to-Server OAuth)
3. Нажмите "View" или "Manage"

### 1.3 Добавьте Feature "Event Subscriptions"
1. В левом меню найдите **"Event Subscriptions"**
2. Нажмите **"+ Add Event Subscription"**

### 1.4 Заполните форму:

**Subscription Name:**
```
Teaching Panel Recording Notifications
```

**Event notification endpoint URL:**
```
https://72.56.81.163/schedule/api/zoom/webhook/
```

> ⚠️ Zoom **ПРОВЕРИТ** этот URL перед сохранением!
> Убедитесь что сервер доступен и webhook handler работает.

### 1.5 Добавьте Event Types

Выберите следующие события:

#### Recording Events (обязательно):
- ✅ `recording.completed` — запись готова
- ✅ `recording.trashed` — запись удалена
- ✅ `recording.deleted` — запись удалена навсегда

#### Meeting Events (опционально):
- ⬜ `meeting.started` — встреча началась
- ⬜ `meeting.ended` — встреча завершена

### 1.6 Сохраните Secret Token

После создания subscription Zoom покажет **Secret Token**.

**ВАЖНО:** Скопируйте и сохраните его! Он нужен для проверки подписи webhook.

Пример:
```
XzY8u_12abCDeFgH3ijKLmnOpQrStuvWxYZ
```

---

## ⚙️ Шаг 2: Настройка на сервере

### 2.1 Добавьте Secret Token в settings.py

```python
# teaching_panel/teaching_panel/settings.py

# Zoom Webhook Secret Token (из шага 1.6)
ZOOM_WEBHOOK_SECRET_TOKEN = 'XzY8u_12abCDeFgH3ijKLmnOpQrStuvWxYZ'
```

### 2.2 Убедитесь что URL доступен

```bash
# На сервере
curl -X POST https://72.56.81.163/schedule/api/zoom/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"event": "test"}'
```

Должны увидеть ответ (не ошибку 404).

### 2.3 Перезапустите Gunicorn

```bash
sudo systemctl restart gunicorn
```

---

## 🧪 Шаг 3: Тестирование

### 3.1 URL Validation Test

При первом сохранении Zoom отправит **validation request**:

```json
{
  "event": "endpoint.url_validation",
  "payload": {
    "plainToken": "abc123..."
  }
}
```

Наш webhook автоматически ответит с `encryptedToken` и Zoom подтвердит URL.

✅ Если все настроено правильно — увидите зеленую галочку в Zoom Marketplace.

### 3.2 Проверка логов

```bash
# Смотрим логи Django
sudo tail -f /var/log/teaching_panel/django.log

# Смотрим логи Celery (фоновые задачи)
sudo tail -f /var/log/teaching_panel/celery.log
```

При срабатывании webhook увидите:
```
INFO Received Zoom webhook: recording.completed
INFO Processing 1 recording files for meeting 123456789
INFO Created LessonRecording 45
INFO Queued 1 recording(s) for processing
```

### 3.3 Тестовая запись урока

1. Создайте урок в системе
2. Включите **"Записывать урок"** (record_lesson = True)
3. Запустите встречу в Zoom
4. Проведите короткую встречу (1-2 минуты)
5. Завершите встречу
6. Подождите 5-10 минут пока Zoom обработает запись
7. **Webhook сработает автоматически!**

Проверьте в логах:
```bash
grep "Processing recording" /var/log/teaching_panel/celery.log
```

Должны увидеть:
```
Processing recording 123 for lesson 456
Downloading recording from Zoom to /var/www/teaching_panel/temp_recordings/lesson_456_xyz.mp4
Uploading to Google Drive: Group A - Math - 2025-01-15 10:00
Successfully uploaded to Google Drive: 1a2b3c4d5e6f...
Successfully processed recording 123
```

---

## 🔒 Безопасность

### Проверка подписи webhook

Наш код автоматически проверяет что webhook **действительно от Zoom**:

```python
# schedule/webhooks.py

def verify_zoom_webhook(request):
    # Получаем подпись из заголовка
    signature = request.headers.get('x-zm-signature')
    
    # Вычисляем HMAC SHA256
    message = f'v0:{timestamp}:{request.body}'
    expected = hmac.new(SECRET_TOKEN, message, sha256).hexdigest()
    
    # Сравниваем
    return hmac.compare_digest(signature, f'v0={expected}')
```

❌ Если подпись не совпадает — запрос отклоняется с 403 Forbidden.

### Защита от replay attacks

Zoom включает `x-zm-request-timestamp` в подпись — старые запросы нельзя переиспользовать.

---

## 📊 Мониторинг

### Проверка статуса webhook в Zoom

1. Zoom Marketplace → Ваше приложение → Event Subscriptions
2. Смотрите **"Last delivery status"**:
   - ✅ **200 OK** — все работает
   - ❌ **403 Forbidden** — неправильный Secret Token
   - ❌ **500 Internal Server Error** — ошибка в коде
   - ❌ **Timeout** — сервер не отвечает

### Логирование событий

Все webhook события логируются в `/var/log/teaching_panel/django.log`:

```bash
# Показать последние webhook события
grep "Received Zoom webhook" /var/log/teaching_panel/django.log | tail -20

# Показать ошибки webhook
grep "Error processing Zoom webhook" /var/log/teaching_panel/django.log | tail -20
```

### Проверка обработанных записей

```bash
cd /var/www/teaching_panel/
python manage.py shell
```

```python
from schedule.models import LessonRecording

# Все записи
LessonRecording.objects.all().count()

# Записи в обработке
LessonRecording.objects.filter(status='processing').count()

# Готовые записи
LessonRecording.objects.filter(status='ready').count()

# Неудачные
failed = LessonRecording.objects.filter(status='failed')
for rec in failed:
    print(f"Lesson {rec.lesson.id}: {rec.zoom_recording_id}")
```

---

## 🆘 Troubleshooting

### Webhook не срабатывает

**Проблема:** Zoom не отправляет события

**Решение:**
1. Проверьте что subscription активен в Zoom Marketplace
2. Убедитесь что выбран event type `recording.completed`
3. Проверьте что URL webhook правильный: `https://72.56.81.163/schedule/api/zoom/webhook/`
4. Убедитесь что SSL сертификат валиден (Zoom требует HTTPS)

### Ошибка "Invalid signature"

**Проблема:** Webhook возвращает 403 Forbidden

**Решение:**
1. Проверьте что `ZOOM_WEBHOOK_SECRET_TOKEN` в settings.py **точно совпадает** с токеном из Zoom
2. Убедитесь что нет лишних пробелов или символов
3. Перезапустите Gunicorn: `sudo systemctl restart gunicorn`

### Записи не загружаются в Google Drive

**Проблема:** Статус остается "processing" или меняется на "failed"

**Решение:**
1. Проверьте логи Celery: `tail -f /var/log/teaching_panel/celery.log`
2. Убедитесь что Google Drive credentials настроены (см. `GDRIVE_SETUP_GUIDE.md`)
3. Проверьте что Celery worker запущен: `systemctl status celery`
4. Попробуйте вручную запустить задачу:
   ```python
   from schedule.tasks import process_zoom_recording
   process_zoom_recording.delay(RECORDING_ID)
   ```

### Zoom recording download timeout

**Проблема:** Запись слишком большая и не успевает скачаться

**Решение:**
1. Увеличьте timeout в `tasks.py`:
   ```python
   response = requests.get(download_url, timeout=600)  # 10 минут
   ```
2. Используйте отдельную Celery queue для больших файлов:
   ```python
   @shared_task(queue='slow_downloads', time_limit=1800)
   def process_zoom_recording(recording_id):
       ...
   ```

### Нет уведомлений ученикам

**Проблема:** Ученики не получают уведомления о записи

**Решение:**
1. Функция `_notify_students_about_recording()` пока не реализована
2. Интегрируйте с вашей системой уведомлений (email, Telegram, push)
3. Или просто покажите записи в личном кабинете без уведомлений

---

## 📈 Следующие шаги

После настройки webhook:

1. ✅ Создайте миграции БД: `python manage.py makemigrations && python manage.py migrate`
2. ✅ Перезапустите все сервисы: `sudo systemctl restart gunicorn celery`
3. ✅ Проведите тестовый урок с записью
4. ✅ Проверьте что запись появилась в Google Drive
5. ✅ Создайте API endpoints для просмотра записей учениками (следующий этап)
6. ✅ Создайте React компоненты для UI записей

---

## 🚀 Автоматизация работает!

Теперь весь процесс **полностью автоматический**:

1. Учитель создает урок и ставит галочку "Записывать урок" ✅
2. Zoom автоматически записывает встречу 🎥
3. Zoom webhook уведомляет нашу систему 🔔
4. Celery task скачивает запись 📥
5. Celery task загружает в Google Drive ☁️
6. Ученики видят запись в ЛК 👀
7. Через 90 дней запись автоматически удаляется 🗑️

**Никакой ручной работы!** 🎉
