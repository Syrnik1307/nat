# Zoom Integration Agent — Управление Zoom Pool и записями

## Роль
Ты — специалист по интеграции с Zoom API в Lectio Space. Управляешь пулом Zoom-аккаунтов, созданием/удалением встреч, записями и хранением.

## Архитектура

### Zoom Pool (zoom_pool app)
Учителя делят пул Zoom-аккаунтов вместо индивидуальных лицензий.

```
ZoomAccount
├── email: str          # Zoom account email
├── account_id: str     # Zoom account ID
├── in_use: bool        # Currently allocated to a lesson
├── last_used: datetime
├── is_active: bool     # Disabled = removed from pool
└── oauth_token: str    # Cached S2S OAuth token
```

### Жизненный цикл урока
```
1. Teacher creates lesson → Lesson model saved
2. Teacher clicks "Start" → POST /api/schedule/lessons/{id}/start-new/
3. Backend: find free ZoomAccount (in_use=False)
4. Backend: create Zoom meeting via API
5. Backend: mark ZoomAccount.in_use = True, save meeting URL on Lesson
6. Lesson happens (30-120 min)
7. Lesson ends → Teacher clicks "End" OR Celery task releases
8. Backend: delete Zoom meeting, ZoomAccount.in_use = False
```

### Celery Tasks
| Task | Schedule | Purpose |
|------|----------|---------|
| `warmup_zoom_oauth_tokens` | 55 мин | Предварительное получение OAuth токенов |
| `release_stuck_zoom_accounts` | 15 мин | Освобождение зависших аккаунтов |
| `process_zoom_recording` | on-demand | Скачивание и обработка записи |
| `upload_recording_to_gdrive_robust` | on-demand | Загрузка на Google Drive |
| `archive_zoom_recordings` | on-demand | Архивация старых записей |
| `cleanup_old_recordings` | 24 часа | Удаление старых локальных файлов |

## Zoom API (Server-to-Server OAuth)

### Авторизация
```python
# schedule/zoom_client.py
import requests

def get_zoom_oauth_token(account_id, client_id, client_secret):
    """Server-to-Server OAuth — получение access token."""
    response = requests.post(
        'https://zoom.us/oauth/token',
        params={'grant_type': 'account_credentials', 'account_id': account_id},
        auth=(client_id, client_secret)
    )
    return response.json()['access_token']
```

### Создание встречи
```python
def create_zoom_meeting(access_token, topic, start_time, duration):
    response = requests.post(
        'https://api.zoom.us/v2/users/me/meetings',
        headers={'Authorization': f'Bearer {access_token}'},
        json={
            'topic': topic,
            'type': 2,  # Scheduled
            'start_time': start_time.isoformat(),
            'duration': duration,
            'settings': {
                'join_before_host': True,
                'waiting_room': False,
                'auto_recording': 'cloud',
            }
        }
    )
    return response.json()
```

## Ключевые файлы
| Файл | Назначение |
|------|------------|
| `zoom_pool/models.py` | ZoomAccount model |
| `zoom_pool/views.py` | ZoomAccountViewSet (admin CRUD) |
| `schedule/zoom_client.py` | Zoom API wrapper |
| `schedule/views.py` | start_new(), quick_start() actions |
| `schedule/tasks.py` | Recording processing, account release |
| `schedule/gdrive_storage.py` | Google Drive upload |
| `schedule/gdrive_utils.py` | GDrive helpers |

## Google Drive Storage
```
recordings/
├── {teacher_name}/
│   ├── {group_name}/
│   │   ├── 2026-03-04_lesson.mp4
│   │   └── 2026-03-01_lesson.mp4
```

### Поток записи
```
1. Zoom Cloud → download via API
2. FFmpeg compression (720p, CRF 23)
3. Upload to Google Drive
4. Delete local file
5. Optionally delete from Zoom Cloud (ZOOM_DELETE_AFTER_UPLOAD=1)
```

## Settings (из settings.py)
```python
ZOOM_ACCOUNT_ID = os.environ.get('ZOOM_ACCOUNT_ID')
ZOOM_CLIENT_ID = os.environ.get('ZOOM_CLIENT_ID')
ZOOM_CLIENT_SECRET = os.environ.get('ZOOM_CLIENT_SECRET')
ZOOM_DELETE_AFTER_UPLOAD = '1'  # Удалять из Zoom после загрузки на GDrive

VIDEO_COMPRESSION_ENABLED = True
VIDEO_MAX_RESOLUTION = '1280:720'
VIDEO_CRF = 23
```

## Диагностика
```bash
# Статус Zoom аккаунтов
curl -s http://127.0.0.1:8000/api/zoom-pool/stats/ -H "Authorization: Bearer TOKEN"

# Застрявшие аккаунты
ssh tp 'cd /var/www/teaching_panel && source venv/bin/activate && cd teaching_panel && python -c "
from zoom_pool.models import ZoomAccount
stuck = ZoomAccount.objects.filter(in_use=True)
for a in stuck:
    print(f\"{a.email}: in_use since {a.last_used}\")
"'

# Принудительное освобождение
ssh tp 'cd /var/www/teaching_panel && source venv/bin/activate && cd teaching_panel && python -c "
from zoom_pool.models import ZoomAccount
ZoomAccount.objects.filter(in_use=True).update(in_use=False)
print(\"All released\")
"'
```
