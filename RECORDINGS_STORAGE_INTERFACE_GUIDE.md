# Руководство по системе хранения и интерфейсу записей уроков

Документ описывает полную архитектуру системы записи уроков Teaching Panel, включая хранение видео на Google Drive, автоматическую обработку через Zoom webhooks, управление квотами, UI для преподавателей и учеников, а также возможности автоматического сжатия записей.

---

## 1. Архитектура системы

### 1.1 Хранение записей (Google Drive)

**Текущее решение**: Записи хранятся на **личном Google Drive разработчика** через Service Account с доступом к выделенной папке.

**Почему Google Drive:**
- Бесплатное хранилище (в рамках лимитов Google Workspace)
- Встроенный видеоплеер с поддержкой адаптивного стриминга
- Простое API для загрузки/удаления/управления файлами
- Возможность прямого воспроизведения через embed URL
- Автоматические превью (thumbnails) для видео

**Структура хранения:**
```
Google Drive (Personal)
└── Teaching Panel Recordings/          # Корневая папка (GDRIVE_RECORDINGS_FOLDER_ID)
    ├── Group A - Math - 2025-12-02 10:00.mp4
    ├── Group B - Physics - 2025-12-02 14:00.mp4
    └── ...
```

**Service Account настройка:**
- Создан в Google Cloud Console с доступом к Drive API
- JSON credentials загружены на сервер (`gdrive-credentials.json`)
- Права Editor на папку "Teaching Panel Recordings"
- Идентификатор папки: `GDRIVE_RECORDINGS_FOLDER_ID` в `settings.py`

**Ограничения:**
- Лимит на количество файлов зависит от квоты Google Drive владельца
- Размер одного файла: до 5 TB (в теории), практически ~10 GB для плавного воспроизведения
- Скорость загрузки/скачивания зависит от сети и тарифа Google

---

### 1.2 Поток обработки записей

```
┌──────────────┐
│  Преподаватель│
│  создает урок │──► [✓] record_lesson = True
└───────┬───────┘    [90] recording_available_for_days
        │
        ▼
┌────────────────┐
│  Zoom Meeting  │
│  автозапись    │◄── Zoom автоматически записывает при старте
└────────┬───────┘
         │ (занятие завершилось)
         ▼
┌─────────────────────┐
│  Zoom Cloud Storage │
│  обработка...       │──► ~5-10 минут для конвертации
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │    Webhook   │──► POST /schedule/api/zoom/webhook/
    │  recording.  │     { event: "recording.completed", payload: {...} }
    │  completed   │
    └──────┬───────┘
           │
           ▼
    ┌────────────────┐
    │  webhooks.py   │──► 1. Проверяет подпись Zoom
    │  Handler       │──► 2. Создает LessonRecording (status=processing)
    └────────┬───────┘──► 3. Запускает Celery task
             │
             ▼
      ┌──────────────────┐
      │   tasks.py       │──► process_zoom_recording()
      │   Celery Task    │
      └─────────┬────────┘
                │
      ┌─────────┴────────┐
      │                  │
      ▼                  ▼
┌──────────┐      ┌────────────────┐
│  Zoom    │      │ Google Drive   │
│ download │──►───│   upload       │──► gdrive_utils.py::upload_recording()
└──────────┘      └────────┬───────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  LessonRecording│──► status = 'ready'
                  │  gdrive_file_id │──► gdrive_file_id = '1a2b3c...'
                  │  play_url       │──► play_url для embed
                  │  file_size      │──► file_size_bytes
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ TeacherStorageQuota│──► add_recording(file_size)
                  │  used_bytes +=  │──► Обновляет квоту преподавателя
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Ученики       │──► Могут смотреть через RecordingsPage
                  │   Преподаватель │──► Управляет через TeacherRecordingsPage
                  └─────────────────┘
                           │
                           │ После recording_available_for_days дней
                           ▼
                  ┌─────────────────┐
                  │  Celery Beat    │──► cleanup_old_recordings()
                  │  Daily cleanup  │──► Удаляет из Google Drive
                  │  03:00 UTC      │──► Освобождает квоту
                  └─────────────────┘
```

---

## 2. Модели данных

### 2.1 Lesson (запись урока)

```python
# teaching_panel/schedule/models.py

class Lesson(models.Model):
    # ... существующие поля ...
    
    record_lesson = models.BooleanField(
        'записывать урок',
        default=False,
        help_text='Автоматически записывать урок в Zoom и сохранять в Google Drive'
    )
    
    recording_available_for_days = models.IntegerField(
        'доступность записи (дней)',
        default=90,
        help_text='Сколько дней запись будет доступна ученикам (0 = бессрочно)'
    )
```

### 2.2 LessonRecording (запись видео)

```python
class LessonRecording(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='recordings')
    
    # Zoom данные
    zoom_recording_id = models.CharField(max_length=100, blank=True)
    download_url = models.URLField(blank=True)  # Временная ссылка Zoom
    play_url = models.URLField(blank=True)      # Ссылка для просмотра
    
    # Google Drive хранение
    storage_provider = models.CharField(max_length=20, default='gdrive')
    gdrive_file_id = models.CharField(max_length=100, blank=True)
    gdrive_folder_id = models.CharField(max_length=100, blank=True)
    archive_url = models.URLField(blank=True)   # Постоянная ссылка Drive
    archive_key = models.CharField(max_length=500, blank=True)
    thumbnail_url = models.URLField(blank=True)
    
    # Метаданные
    file_size = models.BigIntegerField(null=True, blank=True)  # байты
    duration = models.IntegerField(null=True, blank=True)       # секунды
    recording_start = models.DateTimeField(null=True, blank=True)
    recording_end = models.DateTimeField(null=True, blank=True)
    
    # Статус обработки
    status = models.CharField(
        max_length=20,
        choices=[
            ('processing', 'Обрабатывается'),
            ('ready', 'Готова'),
            ('archived', 'Архивирована'),
            ('failed', 'Ошибка'),
            ('deleted', 'Удалена'),
        ],
        default='processing'
    )
    
    # Доступность и аналитика
    available_until = models.DateTimeField(null=True, blank=True)
    views_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 2.3 TeacherStorageQuota (квота хранилища)

```python
class TeacherStorageQuota(models.Model):
    teacher = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='storage_quota')
    
    # Квоты (байты)
    total_quota_bytes = models.BigIntegerField(default=5368709120)  # 5 GB по умолчанию
    used_bytes = models.BigIntegerField(default=0)
    
    # Метрики
    recordings_count = models.IntegerField(default=0)
    purchased_gb = models.IntegerField(default=0)  # Докуплено GB сверх базы
    
    # Уведомления
    warning_sent = models.BooleanField(default=False)       # Предупреждение при 80%
    last_warning_at = models.DateTimeField(null=True, blank=True)
    quota_exceeded = models.BooleanField(default=False)     # Квота превышена
    
    @property
    def total_gb(self):
        return self.total_quota_bytes / (1024 ** 3)
    
    @property
    def used_gb(self):
        return self.used_bytes / (1024 ** 3)
    
    @property
    def usage_percent(self):
        if self.total_quota_bytes == 0:
            return 0
        return (self.used_bytes / self.total_quota_bytes) * 100
    
    def can_upload(self, file_size_bytes):
        return (self.used_bytes + file_size_bytes) <= self.total_quota_bytes
    
    def add_recording(self, file_size_bytes):
        self.used_bytes += file_size_bytes
        self.recordings_count += 1
        if self.used_bytes >= self.total_quota_bytes:
            self.quota_exceeded = True
        if self.usage_percent >= 80 and not self.warning_sent:
            self.warning_sent = True
            self.last_warning_at = timezone.now()
        self.save()
    
    def remove_recording(self, file_size_bytes):
        self.used_bytes = max(0, self.used_bytes - file_size_bytes)
        self.recordings_count = max(0, self.recordings_count - 1)
        if self.used_bytes < self.total_quota_bytes:
            self.quota_exceeded = False
        if self.usage_percent < 80:
            self.warning_sent = False
        self.save()
    
    def increase_quota(self, additional_gb):
        additional_bytes = int(additional_gb * (1024 ** 3))
        self.total_quota_bytes += additional_bytes
        self.purchased_gb += additional_gb
        self.save()
```

---

## 3. Backend API

### 3.1 Просмотр записей (ученики)

**Endpoint:** `GET /schedule/api/recordings/`  
**Права:** `IsAuthenticated` (ученик видит только записи своих групп)

```python
# teaching_panel/schedule/views.py

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_recordings_list(request):
    """Список записей доступных ученику"""
    user = request.user
    if user.role == 'student':
        recordings = LessonRecording.objects.filter(
            lesson__group__students=user,
            status='ready',
            available_until__gte=timezone.now()  # Еще не истекла
        ).select_related('lesson', 'lesson__group').order_by('-lesson__start_time')
    else:
        return Response({'error': 'Доступ запрещен'}, status=403)
    
    serializer = LessonRecordingSerializer(recordings, many=True)
    return Response(serializer.data)
```

### 3.2 Управление записями (преподаватели)

**Endpoint:** `GET /schedule/api/recordings/teacher/`  
**Права:** `IsAuthenticated` (роль teacher)

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_recordings_list(request):
    """Список записей преподавателя"""
    user = request.user
    if user.role != 'teacher':
        return Response({'error': 'Доступ запрещен'}, status=403)
    
    recordings = LessonRecording.objects.filter(
        lesson__teacher=user
    ).select_related('lesson', 'lesson__group').order_by('-created_at')
    
    serializer = LessonRecordingSerializer(recordings, many=True)
    return Response(serializer.data)
```

**Endpoint:** `POST /schedule/api/recordings/{id}/view/`  
**Описание:** Увеличить счетчик просмотров

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recording_view(request, recording_id):
    recording = get_object_or_404(LessonRecording, id=recording_id)
    recording.views_count += 1
    recording.save(update_fields=['views_count'])
    return Response({'views': recording.views_count})
```

**Endpoint:** `DELETE /schedule/api/recordings/{id}/`  
**Описание:** Удалить запись (только учитель)

```python
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_recording(request, recording_id):
    recording = get_object_or_404(LessonRecording, id=recording_id)
    if recording.lesson.teacher != request.user:
        return Response({'error': 'Нет прав'}, status=403)
    
    # Удалить из Google Drive
    if recording.gdrive_file_id:
        gdrive = get_gdrive_manager()
        gdrive.delete_file(recording.gdrive_file_id)
    
    # Освободить квоту
    if recording.file_size:
        try:
            quota = TeacherStorageQuota.objects.get(teacher=recording.lesson.teacher)
            quota.remove_recording(recording.file_size)
        except TeacherStorageQuota.DoesNotExist:
            pass
    
    recording.delete()
    return Response({'message': 'Запись удалена'})
```

### 3.3 Загрузка записей вручную

**Endpoint:** `POST /schedule/api/lessons/{id}/upload_recording/`  
**Описание:** Загрузить видео для конкретного урока

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_recording(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, teacher=request.user)
    
    if 'video' not in request.FILES:
        return Response({'error': 'Файл не загружен'}, status=400)
    
    video_file = request.FILES['video']
    file_size = video_file.size
    
    # Проверить квоту
    try:
        quota = TeacherStorageQuota.objects.get(teacher=request.user)
        if not quota.can_upload(file_size):
            return Response({'error': 'Превышена квота хранилища'}, status=403)
    except TeacherStorageQuota.DoesNotExist:
        quota = TeacherStorageQuota.objects.create(teacher=request.user)
    
    # Загрузить в Google Drive
    gdrive = get_gdrive_manager()
    file_name = f"{lesson.group.name} - {lesson.title} - {timezone.now().strftime('%Y-%m-%d %H:%M')}.mp4"
    file_id = gdrive.upload_file(video_file, file_name)
    
    # Создать запись
    recording = LessonRecording.objects.create(
        lesson=lesson,
        storage_provider='gdrive',
        gdrive_file_id=file_id,
        file_size=file_size,
        status='ready',
        available_until=timezone.now() + timedelta(days=lesson.recording_available_for_days) if lesson.recording_available_for_days > 0 else None
    )
    
    # Обновить квоту
    quota.add_recording(file_size)
    
    return Response(LessonRecordingSerializer(recording).data, status=201)
```

---

## 4. Frontend UI

### 4.1 Страница записей для учеников

**Компонент:** `frontend/src/modules/Recordings/RecordingsPage.js`

**Функционал:**
- Список всех доступных записей с превью
- Фильтрация по группе, предмету, дате
- Поиск по названию урока
- Плеер для воспроизведения (встроенный Google Drive player)
- Счетчик просмотров
- Индикатор "Новая запись" (если < 7 дней)

**Макет:**
```
┌─────────────────────────────────────────┐
│ 📹 Записи уроков                        │
│ [Поиск...]  [Группа ▾] [Предмет ▾]      │
├─────────────────────────────────────────┤
│ ┌──────────┐  ┌──────────┐  ┌──────────┐│
│ │ [Превью] │  │ [Превью] │  │ [Превью] ││
│ │ Математика│  │ Физика   │  │ Химия   ││
│ │ 02.12.2025│  │ 01.12.2025│  │30.11.2025││
│ │ 👁 15     │  │ 👁 8     │  │ 👁 23    ││
│ │ [Смотреть]│  │ [Смотреть]│  │ [Смотреть]││
│ └──────────┘  └──────────┘  └──────────┘│
│ ...                                      │
└─────────────────────────────────────────┘
```

### 4.2 Страница управления записями (преподаватель)

**Компонент:** `frontend/src/modules/Recordings/TeacherRecordingsPage.js`

**Функционал:**
- Все записи преподавателя с детальной статистикой
- Статусы обработки (готово / обрабатывается / ошибка)
- Кнопка "Загрузить видео" для ручной загрузки
- Удаление записей с подтверждением
- Фильтры по группе, статусу
- Прогресс-бар квоты хранилища

**Макет:**
```
┌─────────────────────────────────────────┐
│ 📹 Записи моих уроков    [⬆ Загрузить] │
├─────────────────────────────────────────┤
│ Квота: 2.3 / 5.0 GB  [████░░░░░] 46%   │
├─────────────────────────────────────────┤
│ Статистика:                              │
│ [📊 42 Всего] [✅ 38 Готово] [⏳ 3 Обрабатывается] [❌ 1 Ошибка] │
├─────────────────────────────────────────┤
│ [Поиск...] [Группа ▾] [Статус ▾] [🔄]   │
├─────────────────────────────────────────┤
│ ┌──────────┐  ┌──────────┐  ┌──────────┐│
│ │ [Превью] │  │ [Превью] │  │ [Превью] ││
│ │ Группа A │  │ Группа B │  │ Группа C ││
│ │ 02.12    │  │ 01.12    │  │ 30.11    ││
│ │ 👁 15 🗑️  │  │ ⏳ 🗑️     │  │ 👁 8 🗑️  ││
│ └──────────┘  └──────────┘  └──────────┘│
└─────────────────────────────────────────┘
```

### 4.3 Модальное окно загрузки

**Функционал:**
- Drag & drop интерфейс для видео файлов
- Выбор урока (или создание standalone записи)
- Настройка приватности (все / конкретные группы / ученики)
- Прогресс-бар загрузки
- Валидация формата (только video/*)
- Проверка квоты до загрузки

---

## 5. Автоматическое сжатие записей

### 5.1 Обоснование

**Проблема:** Видео занятий часто весят 500 MB - 2 GB за час, быстро исчерпывая квоту.

**Решение:** Автоматическое сжатие через FFmpeg без потери визуального качества.

**Целевые параметры:**
- **Видеокодек:** H.264 (x264) с пресетом `medium`
- **Битрейт:** Динамический (VBR), целевой ~1 Mbps для 720p
- **Разрешение:** 1280x720 (если исходное выше)
- **Аудиокодек:** AAC, 128 kbps
- **Результат:** Уменьшение размера на 60-80% без заметной потери качества для учебных целей

### 5.2 Реализация

#### Установка FFmpeg на сервере

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg -y

# Проверка
ffmpeg -version
```

#### Python обертка (gdrive_utils.py)

```python
import subprocess
import tempfile
import os

def compress_video(input_path, output_path):
    """
    Сжимает видео через FFmpeg
    
    Параметры:
    - input_path: путь к исходному файлу
    - output_path: путь к сжатому файлу
    
    Возвращает:
    - True если успешно, False если ошибка
    """
    try:
        # FFmpeg команда для оптимального сжатия
        cmd = [
            'ffmpeg',
            '-i', input_path,                    # Входной файл
            '-c:v', 'libx264',                   # Видеокодек H.264
            '-preset', 'medium',                 # Баланс скорость/качество
            '-crf', '23',                        # Constant Rate Factor (18-28, 23 = хорошее качество)
            '-vf', 'scale=1280:720',             # Масштабировать до 720p
            '-c:a', 'aac',                       # Аудиокодек AAC
            '-b:a', '128k',                      # Битрейт аудио
            '-movflags', '+faststart',           # Оптимизация для веб-стриминга
            '-y',                                # Перезаписать если существует
            output_path
        ]
        
        # Запустить FFmpeg
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3600  # Таймаут 1 час
        )
        
        if result.returncode == 0:
            # Проверить что файл создан и меньше оригинала
            if os.path.exists(output_path):
                original_size = os.path.getsize(input_path)
                compressed_size = os.path.getsize(output_path)
                compression_ratio = (1 - compressed_size / original_size) * 100
                
                logger.info(f"Video compressed: {original_size / (1024**2):.1f} MB → {compressed_size / (1024**2):.1f} MB ({compression_ratio:.1f}% reduction)")
                return True
        else:
            logger.error(f"FFmpeg failed: {result.stderr.decode()}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout (>1 hour)")
        return False
    except Exception as e:
        logger.error(f"Compression error: {e}")
        return False
```

#### Интеграция в Celery task

```python
# teaching_panel/schedule/tasks.py

@shared_task
def process_zoom_recording(recording_id):
    """Скачать запись с Zoom, сжать, загрузить в Google Drive"""
    try:
        recording = LessonRecording.objects.get(id=recording_id)
        
        # 1. Скачать с Zoom
        temp_original = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        response = requests.get(recording.download_url, stream=True)
        for chunk in response.iter_content(chunk_size=8192):
            temp_original.write(chunk)
        temp_original.close()
        
        original_size = os.path.getsize(temp_original.name)
        logger.info(f"Downloaded from Zoom: {original_size / (1024**2):.1f} MB")
        
        # 2. Сжать через FFmpeg
        temp_compressed = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_compressed.close()
        
        if compress_video(temp_original.name, temp_compressed.name):
            compressed_size = os.path.getsize(temp_compressed.name)
            upload_file = temp_compressed.name
            final_size = compressed_size
            logger.info(f"Compression successful: {compressed_size / (1024**2):.1f} MB")
        else:
            # Если сжатие не удалось, загрузить оригинал
            logger.warning("Compression failed, uploading original")
            upload_file = temp_original.name
            final_size = original_size
        
        # 3. Загрузить в Google Drive
        gdrive = get_gdrive_manager()
        file_name = f"{recording.lesson.group.name} - {recording.lesson.title} - {recording.created_at.strftime('%Y-%m-%d %H:%M')}.mp4"
        
        with open(upload_file, 'rb') as f:
            file_id = gdrive.upload_file(f, file_name)
        
        # 4. Обновить запись
        recording.gdrive_file_id = file_id
        recording.file_size = final_size
        recording.status = 'ready'
        recording.save()
        
        # 5. Обновить квоту преподавателя
        try:
            quota = TeacherStorageQuota.objects.get(teacher=recording.lesson.teacher)
            quota.add_recording(final_size)
        except TeacherStorageQuota.DoesNotExist:
            quota = TeacherStorageQuota.objects.create(teacher=recording.lesson.teacher)
            quota.add_recording(final_size)
        
        # 6. Удалить временные файлы
        os.remove(temp_original.name)
        if temp_compressed.name != temp_original.name:
            os.remove(temp_compressed.name)
        
        logger.info(f"Recording processed successfully: {file_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing recording {recording_id}: {e}")
        recording.status = 'failed'
        recording.save()
        return False
```

### 5.3 Настройки сжатия

**В `settings.py`:**

```python
# Параметры сжатия видео
VIDEO_COMPRESSION_ENABLED = True
VIDEO_MAX_RESOLUTION = '1280:720'  # 720p
VIDEO_CRF = 23                     # Качество (18-28, чем ниже = лучше)
VIDEO_PRESET = 'medium'            # Скорость сжатия (ultrafast/fast/medium/slow)
AUDIO_BITRATE = '128k'             # Битрейт аудио

# Отключить сжатие для тестирования
# VIDEO_COMPRESSION_ENABLED = False
```

**Преимущества:**
- ✅ Экономия 60-80% места
- ✅ Быстрая загрузка для учеников
- ✅ Меньше нагрузка на Google Drive API
- ✅ Автоматическое масштабирование до 720p (оптимально для учебных целей)

**Недостатки:**
- ⚠️ Дополнительное время обработки (~5-10 минут для часовой записи)
- ⚠️ Требует мощный CPU на сервере
- ⚠️ Может быть заметна небольшая потеря качества на очень детальных изображениях

---

## 6. Управление квотами

### 6.1 Базовая квота

- **По умолчанию:** 5 GB на преподавателя
- Привязана к подписке (см. `accounts/models.py::Subscription`)
- Автоматически создается при первой загрузке записи

### 6.2 Увеличение квоты

**Endpoint:** `POST /accounts/api/admin/teachers/{id}/storage/`  
**Body:** `{ "extra_gb": 10 }`

```python
# teaching_panel/accounts/admin_views.py

class AdminTeacherStorageView(APIView):
    def post(self, request, teacher_id):
        teacher = get_object_or_404(User, id=teacher_id, role='teacher')
        extra_gb = int(request.data.get('extra_gb', 0))
        
        if extra_gb <= 0:
            return Response({'error': 'Укажите количество GB > 0'}, status=400)
        
        subscription = get_subscription(teacher)
        subscription.extra_storage_gb += extra_gb
        subscription.save()
        
        # Также обновить TeacherStorageQuota если существует
        try:
            quota = TeacherStorageQuota.objects.get(teacher=teacher)
            quota.increase_quota(extra_gb)
        except TeacherStorageQuota.DoesNotExist:
            pass
        
        return Response({'message': f'Добавлено {extra_gb} GB'})
```

### 6.3 Уведомления о квоте

**Trigger 1: 80% использования**
- Флаг `warning_sent = True`
- Отправка Telegram уведомления: "⚠️ Использовано 80% хранилища (4.0 / 5.0 GB). Рекомендуем удалить старые записи или увеличить квоту."

**Trigger 2: 100% (квота превышена)**
- Флаг `quota_exceeded = True`
- Блокировка загрузки новых записей
- Уведомление: "❌ Квота хранилища исчерпана! Удалите записи или обратитесь к администратору для увеличения."

**Реализация:**

```python
# teaching_panel/accounts/notifications.py

def notify_storage_quota_warning(teacher):
    """Уведомить о достижении 80% квоты"""
    if not teacher.telegram_chat_id:
        return
    
    quota = teacher.storage_quota
    message = (
        f"⚠️ <b>Внимание!</b>\n\n"
        f"Использовано <b>{quota.usage_percent:.0f}%</b> хранилища записей:\n"
        f"📊 {quota.used_gb:.2f} / {quota.total_gb:.2f} GB\n\n"
        f"Рекомендуем удалить старые записи или увеличить квоту."
    )
    
    send_telegram_notification(teacher.telegram_chat_id, message)
    
def notify_storage_quota_exceeded(teacher):
    """Уведомить о превышении квоты"""
    if not teacher.telegram_chat_id:
        return
    
    quota = teacher.storage_quota
    message = (
        f"❌ <b>Квота исчерпана!</b>\n\n"
        f"Хранилище записей переполнено:\n"
        f"📊 {quota.used_gb:.2f} / {quota.total_gb:.2f} GB\n\n"
        f"Новые записи не будут сохраняться.\n"
        f"Удалите записи или обратитесь к администратору."
    )
    
    send_telegram_notification(teacher.telegram_chat_id, message)
```

---

## 7. Чек-лист реализации

### Backend
- [x] Модели `Lesson`, `LessonRecording`, `TeacherStorageQuota`
- [x] Zoom webhook handler (`webhooks.py`)
- [x] Google Drive интеграция (`gdrive_utils.py`)
- [x] Celery task `process_zoom_recording`
- [x] Celery task `cleanup_old_recordings`
- [x] API endpoints для записей (список, детали, удаление)
- [x] Endpoint загрузки вручную
- [x] Проверка квот при загрузке
- [ ] FFmpeg сжатие (опционально, готово к интеграции)
- [ ] Уведомления о квоте (интеграция с Telegram)

### Frontend
- [x] `RecordingsPage.js` (ученики)
- [x] `TeacherRecordingsPage.js` (преподаватели)
- [x] `RecordingCard.js` (карточка записи)
- [x] `RecordingPlayer.js` (встроенный плеер)
- [ ] Drag & drop загрузка (частично готово)
- [ ] Прогресс-бар квоты на дашборде
- [ ] Модальное окно настройки приватности

### Инфраструктура
- [x] Google Drive Service Account настроен
- [x] Zoom webhook зарегистрирован
- [x] Celery worker запущен
- [x] Celery beat для cleanup настроен
- [ ] FFmpeg установлен на сервере
- [ ] Мониторинг квот (dashboard)

---

## 8. Советы по отладке

### Записи не создаются после урока
1. Проверить `record_lesson=True` на уроке
2. Проверить Zoom webhook в логах: `sudo journalctl -u teaching_panel | grep webhook`
3. Убедиться что Celery worker запущен: `sudo systemctl status celery`
4. Проверить наличие записи в Zoom Cloud Storage (может быть долгая обработка)

### Сжатие не работает
1. Установить FFmpeg: `sudo apt install ffmpeg -y`
2. Проверить версию: `ffmpeg -version` (должна быть >= 4.0)
3. Проверить логи Celery: `sudo tail -f /var/log/celery.log | grep compress`
4. Отключить сжатие временно: `VIDEO_COMPRESSION_ENABLED = False` в `settings.py`

### Квота не обновляется
1. Проверить существование `TeacherStorageQuota`: `python manage.py shell` → `TeacherStorageQuota.objects.all()`
2. Убедиться что `add_recording()` вызывается после загрузки
3. Проверить синхронизацию между `Subscription.extra_storage_gb` и `TeacherStorageQuota.total_quota_bytes`

### Google Drive ошибка 403
1. Проверить что Service Account имеет права Editor на папку
2. Убедиться что `gdrive-credentials.json` читаем: `chmod 600 gdrive-credentials.json`
3. Проверить `GDRIVE_RECORDINGS_FOLDER_ID` в `settings.py`

---

## 9. Будущие улучшения

1. **Адаптивный битрейт:** Использовать HLS/DASH для автоматической подстройки качества под скорость интернета
2. **Субтитры:** Автогенерация субтитров через Google Speech-to-Text API
3. **Закладки:** Позволить ученикам ставить метки времени с комментариями
4. **Офлайн режим:** Загрузка записей для просмотра без интернета (мобильное приложение)
5. **AI анализ:** Автоматическое выделение ключевых моментов урока
6. **Миграция на S3/Azure:** Если Google Drive лимиты станут проблемой

---

Следуя этому руководству, можно полностью управлять системой записей уроков, от автоматического захвата через Zoom до ручной загрузки, с гибким контролем квот и автоматическим сжатием для экономии места.
