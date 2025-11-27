# 📹 Система записи уроков — Быстрый старт

## ✅ Что уже готово

### 1. База данных
- ✅ Модель `Lesson` с полями `record_lesson` и `recording_available_for_days`
- ✅ Модель `LessonRecording` с поддержкой Google Drive
- ❌ **Нужно:** Запустить миграции

### 2. Google Drive интеграция
- ✅ Класс `GoogleDriveManager` для работы с Drive API
- ✅ Загрузка, удаление, получение ссылок для воспроизведения
- ❌ **Нужно:** Настроить Service Account (см. `GDRIVE_SETUP_GUIDE.md`)

### 3. Zoom Webhook
- ✅ Handler для приема событий `recording.completed`
- ✅ Проверка подписи для безопасности
- ✅ URL validation для Zoom Marketplace
- ❌ **Нужно:** Зарегистрировать webhook в Zoom (см. `ZOOM_WEBHOOK_SETUP.md`)

### 4. Фоновые задачи (Celery)
- ✅ `process_zoom_recording()` — скачать с Zoom → загрузить в Drive
- ✅ `cleanup_old_recordings()` — удалять старые записи
- ✅ Интеграция с существующей системой Zoom Pool
- ❌ **Нужно:** Добавить task в Django-Q/Celery Beat расписание

### 5. Что еще НЕ готово
- ❌ API endpoints для просмотра записей учениками
- ❌ React компоненты для UI (страница "Записи уроков")
- ❌ Интеграция уведомлений ученикам

---

## 🚀 Установка (Шаг за Шагом)

### Шаг 1: Установите зависимости

```bash
cd /var/www/teaching_panel/
source venv/bin/activate
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Или используйте обновленный `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

### Шаг 2: Настройте Google Drive

**Следуйте инструкциям:** [`GDRIVE_SETUP_GUIDE.md`](./GDRIVE_SETUP_GUIDE.md)

**Кратко:**
1. Создайте Service Account в Google Cloud Console
2. Скачайте JSON credentials
3. Создайте папку в Google Drive для записей
4. Поделитесь папкой с Service Account (Editor права)
5. Скопируйте Folder ID
6. Загрузите credentials на сервер:
   ```bash
   scp gdrive-credentials.json root@72.56.81.163:/var/www/teaching_panel/
   chmod 600 gdrive-credentials.json
   ```
7. Добавьте в `settings.py`:
   ```python
   GDRIVE_CREDENTIALS_FILE = os.path.join(BASE_DIR, 'gdrive-credentials.json')
   GDRIVE_RECORDINGS_FOLDER_ID = 'YOUR_FOLDER_ID_HERE'
   ```

---

### Шаг 3: Настройте Zoom Webhook

**Следуйте инструкциям:** [`ZOOM_WEBHOOK_SETUP.md`](./ZOOM_WEBHOOK_SETUP.md)

**Кратко:**
1. Зайдите в Zoom Marketplace
2. Откройте ваше Server-to-Server приложение
3. Добавьте Event Subscription:
   - URL: `https://72.56.81.163/schedule/api/zoom/webhook/`
   - Events: `recording.completed`, `recording.trashed`
4. Скопируйте Secret Token
5. Добавьте в `settings.py`:
   ```python
   ZOOM_WEBHOOK_SECRET_TOKEN = 'YOUR_SECRET_TOKEN_HERE'
   ```

---

### Шаг 4: Примените миграции БД

```bash
cd /var/www/teaching_panel/
source venv/bin/activate
python manage.py makemigrations schedule
python manage.py migrate
```

**Должны увидеть:**
```
Migrations for 'schedule':
  schedule/migrations/0XXX_add_recording_fields.py
    - Add field record_lesson to lesson
    - Add field recording_available_for_days to lesson
    - Add field storage_provider to lessonrecording
    - Add field gdrive_file_id to lessonrecording
    - Add field gdrive_folder_id to lessonrecording
    - Add field thumbnail_url to lessonrecording
    - Add field available_until to lessonrecording
    - Add field views_count to lessonrecording
    - Alter field status on lessonrecording

Running migrations:
  Applying schedule.0XXX_add_recording_fields... OK
```

---

### Шаг 5: Перезапустите сервисы

```bash
# Gunicorn (Django)
sudo systemctl restart gunicorn

# Celery (фоновые задачи)
sudo systemctl restart celery

# Nginx (если нужно)
sudo systemctl restart nginx
```

---

### Шаг 6: Настройте периодическую очистку

Добавьте задачу в Django-Q или Celery Beat для автоудаления старых записей.

**Django-Q:** (если используете)
```python
# В Django Admin → Django Q → Scheduled tasks
Name: cleanup_old_recordings
Function: schedule.tasks.cleanup_old_recordings
Schedule Type: Daily
Repeats: -1 (infinite)
```

**Celery Beat:** (если используете)
```python
# teaching_panel/teaching_panel/celery.py

from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-old-recordings': {
        'task': 'schedule.tasks.cleanup_old_recordings',
        'schedule': crontab(hour=3, minute=0),  # Каждый день в 3:00
    },
}
```

---

### Шаг 7: Тестирование

1. **Проверьте Google Drive подключение:**
   ```bash
   python manage.py shell
   ```
   ```python
   from schedule.gdrive_utils import get_gdrive_manager
   gdrive = get_gdrive_manager()
   print("Google Drive connected successfully!")
   ```

2. **Создайте тестовый урок с записью:**
   - Зайдите в админку Django
   - Создайте новый урок
   - Поставьте галочку **"Записывать урок"** (record_lesson = True)
   - Сохраните

3. **Проведите тестовую встречу:**
   - Запустите урок через систему
   - Подключитесь к Zoom встрече
   - Проговорите что-то для записи (1-2 минуты)
   - Завершите встречу

4. **Подождите 5-10 минут** пока Zoom обработает запись

5. **Проверьте логи:**
   ```bash
   sudo tail -f /var/log/teaching_panel/django.log
   sudo tail -f /var/log/teaching_panel/celery.log
   ```

6. **Проверьте БД:**
   ```python
   from schedule.models import LessonRecording
   recordings = LessonRecording.objects.all()
   for rec in recordings:
       print(f"Lesson {rec.lesson.id}: Status={rec.status}, Drive={rec.gdrive_file_id}")
   ```

7. **Проверьте Google Drive:**
   - Откройте папку "Teaching Panel Recordings" в Drive
   - Должны увидеть загруженный видео файл

---

## 📊 Архитектура потока данных

```
┌─────────────┐
│   Teacher   │
│ Creates     │──► [x] Записывать урок
│   Lesson    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Zoom Meeting   │
│  Auto-records   │◄── Zoom автоматически записывает
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│  Zoom Cloud Storage  │
│  Processing...       │
└──────────┬───────────┘
           │
           ▼
    ┌──────────────┐
    │    Webhook   │──► POST https://72.56.81.163/schedule/api/zoom/webhook/
    │  recording.  │     {event: "recording.completed", object: {...}}
    │  completed   │
    └──────┬───────┘
           │
           ▼
    ┌────────────────┐
    │  webhooks.py   │──► Создает LessonRecording (status=processing)
    │  Webhook       │──► Запускает Celery task
    │  Handler       │
    └────────┬───────┘
             │
             ▼
      ┌──────────────────┐
      │   tasks.py       │
      │   Celery Task    │
      └─────────┬────────┘
                │
      ┌─────────┴────────┐
      │                  │
      ▼                  ▼
┌──────────┐      ┌────────────────┐
│  Zoom    │      │ Google Drive   │
│ download │──►───│   upload       │
└──────────┘      └────────┬───────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  LessonRecording│
                  │  status=ready   │
                  │  gdrive_file_id │
                  │  play_url       │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Students      │
                  │   View in LK    │◄── (TODO: API + React UI)
                  └─────────────────┘
                           │
                           │ После X дней (90)
                           ▼
                  ┌─────────────────┐
                  │  Celery Beat    │
                  │  Daily cleanup  │──► Удаляет из Google Drive
                  └─────────────────┘
```

---

## 📝 Следующие задачи (TODO)

### 1. API Endpoints (backend)
Файл: `teaching_panel/schedule/views.py`

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_recordings_list(request):
    """Список всех записей доступных ученику"""
    student = request.user.student_profile
    recordings = LessonRecording.objects.filter(
        lesson__group__students=student,
        status='ready'
    ).order_by('-lesson__start_time')
    serializer = LessonRecordingSerializer(recordings, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def recording_detail(request, recording_id):
    """Детали конкретной записи + embed URL"""
    recording = get_object_or_404(LessonRecording, id=recording_id)
    # Проверить права доступа
    serializer = LessonRecordingSerializer(recording)
    return Response(serializer.data)

@api_view(['POST'])
def recording_view_count(request, recording_id):
    """Увеличить счетчик просмотров"""
    recording = get_object_or_404(LessonRecording, id=recording_id)
    recording.views_count += 1
    recording.save()
    return Response({'views': recording.views_count})
```

### 2. Serializer (backend)
Файл: `teaching_panel/schedule/serializers.py`

```python
class LessonRecordingSerializer(serializers.ModelSerializer):
    lesson_info = LessonSerializer(source='lesson', read_only=True)
    
    class Meta:
        model = LessonRecording
        fields = [
            'id', 'lesson', 'lesson_info', 'recording_type',
            'file_size', 'play_url', 'thumbnail_url',
            'available_until', 'views_count', 'status',
            'created_at'
        ]
```

### 3. React Component (frontend)
Файл: `frontend/src/modules/Recordings/RecordingsPage.js`

```jsx
import React, { useState, useEffect } from 'react';
import api from '../../apiService';

function RecordingsPage() {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadRecordings();
  }, []);
  
  const loadRecordings = async () => {
    try {
      const response = await api.get('/schedule/api/recordings/');
      setRecordings(response.data);
    } catch (error) {
      console.error('Failed to load recordings:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="recordings-page">
      <h1>📹 Записи уроков</h1>
      {loading ? (
        <p>Загрузка...</p>
      ) : recordings.length === 0 ? (
        <p>Пока нет доступных записей</p>
      ) : (
        <div className="recordings-grid">
          {recordings.map(rec => (
            <RecordingCard key={rec.id} recording={rec} />
          ))}
        </div>
      )}
    </div>
  );
}

function RecordingCard({ recording }) {
  return (
    <div className="recording-card">
      <div className="thumbnail">
        {recording.thumbnail_url ? (
          <img src={recording.thumbnail_url} alt="Preview" />
        ) : (
          <div className="no-thumbnail">🎥</div>
        )}
      </div>
      <div className="info">
        <h3>{recording.lesson_info.subject.name}</h3>
        <p>{new Date(recording.lesson_info.start_time).toLocaleDateString('ru-RU')}</p>
        <p>Просмотров: {recording.views_count}</p>
        <button onClick={() => openPlayer(recording)}>
          Смотреть
        </button>
      </div>
    </div>
  );
}
```

### 4. Video Player Component
Файл: `frontend/src/modules/Recordings/RecordingPlayer.js`

```jsx
function RecordingPlayer({ recordingId, playUrl }) {
  const trackView = async () => {
    await api.post(`/schedule/api/recordings/${recordingId}/view/`);
  };
  
  useEffect(() => {
    trackView();
  }, [recordingId]);
  
  return (
    <div className="recording-player">
      <iframe
        src={playUrl}
        width="100%"
        height="600px"
        frameBorder="0"
        allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
      />
    </div>
  );
}
```

---

## 🎯 Критерии готовности

- [x] Database models created
- [x] Google Drive utilities implemented
- [x] Zoom webhook handler created
- [x] Celery background tasks created
- [x] Dependencies added to requirements.txt
- [x] Documentation written (setup guides)
- [ ] Database migrations applied ← **СДЕЛАЙТЕ ЭТО СЕЙЧАС**
- [ ] Google Service Account configured
- [ ] Zoom webhook registered
- [ ] API endpoints created
- [ ] Serializers created
- [ ] React components created
- [ ] Navigation menu updated (add "Recordings" link)
- [ ] Permissions configured (students can only see their recordings)
- [ ] Tested end-to-end

---

## 📞 Помощь

Если что-то не работает:

1. **Проверьте логи:**
   ```bash
   sudo tail -f /var/log/teaching_panel/django.log
   sudo tail -f /var/log/teaching_panel/celery.log
   ```

2. **Проверьте статус сервисов:**
   ```bash
   sudo systemctl status gunicorn
   sudo systemctl status celery
   sudo systemctl status redis
   ```

3. **Проверьте БД:**
   ```bash
   python manage.py shell
   from schedule.models import LessonRecording
   LessonRecording.objects.all()
   ```

4. **Тестируйте компоненты по отдельности:**
   - Google Drive: `from schedule.gdrive_utils import get_gdrive_manager; gdrive = get_gdrive_manager()`
   - Zoom webhook: `curl -X POST http://localhost:8000/schedule/api/zoom/webhook/`
   - Celery task: `from schedule.tasks import cleanup_old_recordings; cleanup_old_recordings()`

---

Готово к запуску! 🚀
