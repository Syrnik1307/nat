# Паттерны Celery задач

- **Тип**: Архитектурный паттерн
- **Компоненты**: Celery, Redis, schedule/tasks.py, accounts/tasks.py

## 4 очереди

| Очередь | Назначение | Пример задач |
|---------|-----------|-------------|
| default | Обычные задачи | send_email, sync_data |
| heavy | Тяжёлые (долгие) | grade_homework_batch, export_analytics |
| notifications | Уведомления | send_telegram, send_push |
| periodic | Периодические | cleanup, warmup_tokens |

## Паттерн надёжной задачи
```python
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=300,
    soft_time_limit=270,
)
def reliable_task(self, arg):
    try:
        # логика
        pass
    except SoftTimeLimitExceeded:
        # cleanup
        raise
    except TransientError as e:
        raise self.retry(exc=e)
```

## Anti-patterns
- НЕ передавать ORM-объекты в задачу — только ID
- НЕ делать задачи больше 5 минут без time_limit
- НЕ запускать несколько beat-процессов
- НЕ использовать `delay()` для критичных задач — использовать `apply_async(queue='...')`

## Мониторинг
```bash
# Статус worker
ssh tp 'celery -A teaching_panel inspect active'

# Задачи в очереди
ssh tp 'celery -A teaching_panel inspect reserved'

# Beat расписание
ssh tp 'celery -A teaching_panel inspect scheduled'
```
