# Celery Tasks Agent — Управление фоновыми задачами

## Роль
Ты — специалист по Celery/Redis в Lectio Space. Создаёшь, отлаживаешь и оптимизируешь фоновые задачи.

## Инфраструктура
- **Celery**: 4 очереди (default, heavy, notifications, periodic)
- **Redis**: broker + result backend
- **Workers**: solo pool (Windows dev), prefork (Linux prod)
- **Beat**: django-celery-beat для расписания
- **Server**: 2GB RAM — критически важна экономия памяти

## Текущие очереди и маршрутизация
| Queue | Задачи | Назначение |
|-------|--------|------------|
| `default` | Всё остальное | Лёгкие задачи |
| `heavy` | process_zoom_recording, upload_recording_to_gdrive_robust, archive_zoom_recordings, sync_teacher_storage_usage | Видео, GDrive |
| `notifications` | send_lesson_reminder, check_expiring_subscriptions, send_student_*_warnings, process_scheduled_messages | Email, Telegram |
| `periodic` | warmup_zoom_oauth_tokens, release_stuck_zoom_accounts, process_expired_subscriptions | По расписанию |

## Текущее расписание (CELERY_BEAT_SCHEDULE)
| Задача | Интервал | Очередь |
|--------|----------|---------|
| warmup-zoom-oauth-tokens | 55 мин | periodic |
| release-stuck-zoom-accounts | 15 мин | periodic |
| schedule-lesson-reminders | 10 мин | notifications |
| send-recurring-lesson-reminders | 2 мин | notifications |
| check-expiring-subscriptions | 6 часов | notifications |
| process-expired-subscriptions | 1 час | periodic |
| sync-teacher-storage-usage | 6 часов | heavy |
| cleanup-old-recordings | 24 часа | heavy |
| process-ai-grading-queue | 30 сек | default |
| process-scheduled-messages | 1 мин | notifications |
| monitor-rate-limiting | 15 мин | periodic |
| send-weekly-revenue-report | пн 10:00 | notifications |

## Паттерн создания задачи
```python
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(
    name='myapp.tasks.my_task',       # Явное имя (обязательно!)
    bind=True,                         # Доступ к self для retry
    max_retries=3,
    default_retry_delay=60,            # 1 мин между retries
    soft_time_limit=300,               # 5 мин soft limit
    time_limit=600,                    # 10 мин hard limit
    acks_late=True,                    # Подтверждение после выполнения
    reject_on_worker_lost=True,        # Возврат в очередь при crash
)
def my_task(self, param1, param2):
    """Описание задачи."""
    try:
        logger.info(f"Starting my_task: {param1}")
        # Логика
        result = do_something(param1, param2)
        logger.info(f"Completed my_task: {result}")
        return result
    except SoftTimeLimitExceeded:
        logger.warning(f"my_task soft timeout: {param1}")
        return None
    except Exception as exc:
        logger.error(f"my_task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
```

## Чеклист при создании задачи
1. `name=` — явное имя (формат: `app.tasks.task_name`)
2. Добавить app в `CELERY_IMPORTS` в settings.py
3. Если periodic → добавить в `CELERY_BEAT_SCHEDULE`
4. Если тяжёлая → маршрутизировать в `heavy` очередь через `CELERY_TASK_ROUTES`
5. Если notification → в `notifications` очередь
6. Retry с exponential backoff для внешних API
7. Логирование начала и конца выполнения
8. Soft/hard time limits

## Диагностика
```bash
# Статус workers
ssh tp 'cd /var/www/teaching_panel && source venv/bin/activate && celery -A teaching_panel inspect active'

# Очереди Redis
ssh tp 'redis-cli llen default && redis-cli llen heavy && redis-cli llen notifications'

# Лог worker
ssh tp 'journalctl -u teaching_panel-celery-worker --since "30 min ago" --no-pager | tail -30'

# Лог beat
ssh tp 'journalctl -u teaching_panel-celery-beat --since "1 hour ago" --no-pager | tail -20'

# Принудительный рестарт
ssh tp 'sudo systemctl restart teaching_panel-celery-worker teaching_panel-celery-beat'
```

## Оптимизация для 2GB RAM
- `CELERY_WORKER_MAX_TASKS_PER_CHILD = 50` — рестарт после 50 задач
- `CELERY_WORKER_MAX_MEMORY_PER_CHILD = 150000` — 150MB лимит
- `CELERY_WORKER_PREFETCH_MULTIPLIER = 1` — по 1 задаче
- Heavy задачи в отдельную очередь (не блокируют notifications)
