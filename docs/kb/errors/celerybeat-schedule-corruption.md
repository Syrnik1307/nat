# Celerybeat Schedule Corruption / Permission Denied

- **Дата**: 2026-01 (повторяющаяся)
- **Severity**: MEDIUM
- **Компонент**: Celery Beat
- **Источник**: @prod-monitor / @celery-tasks

## Симптомы
```
error: [Errno 13] Permission denied: 'celerybeat-schedule'
error: db type could not be determined
```

## Причина
Файл `celerybeat-schedule` (shelve/dbm) повреждён из-за:
- Некорректного завершения celery-beat (kill -9, OOM)
- Одновременного запуска нескольких beat-процессов
- Обновления версии Celery/Python

## Решение
```bash
sudo systemctl stop celery-beat
sudo rm -f /var/www/teaching_panel/teaching_panel/celerybeat-schedule*
# НЕ создавать файл вручную! Celery сам создаст
sudo systemctl start celery-beat
file /var/www/teaching_panel/teaching_panel/celerybeat-schedule
# Должно показать: GNU dbm 1.x or ndbm database
```

## Профилактика
- Не запускать несколько beat: `pgrep -af "celery.*beat"`
- Graceful shutdown: `systemctl stop`, не `kill -9`
- Опционально: перейти на `DatabaseScheduler` (django-celery-beat)

## Связь
- Определения задач в коде (CELERY_BEAT_SCHEDULE) — не потеряются при удалении файла
- См. также: [gunicorn-oom-sigkill.md](gunicorn-oom-sigkill.md) — OOM может убить beat
