# Ошибка: Permission denied: 'celerybeat-schedule'

## Симптомы

В Sentry/логах появляется ошибка:
```
error: [Errno 13] Permission denied: 'celerybeat-schedule'
Removing corrupted schedule file 'celerybeat-schedule': error(13, 'Permission denied')
```

**Источник**: Celery Beat scheduler при запуске или обновлении расписания.

## Причина

Файл `celerybeat-schedule` — это shelve-база данных, где Celery Beat хранит информацию о последнем запуске периодических задач. Ошибка возникает когда:

1. **Файл повреждён** — Celery пытается удалить и пересоздать, но не может
2. **Неправильные права** — процесс celery-beat не имеет прав на запись
3. **Файл заблокирован** — другой процесс держит файл открытым

### Типичные причины повреждения:
- Некорректное завершение celery-beat (kill -9, сбой питания)
- Одновременный запуск нескольких экземпляров celery-beat
- Обновление версии Celery/Python с изменением формата shelve

## Быстрое решение

```bash
# 1. Остановить celery-beat
sudo systemctl stop celery-beat

# 2. Удалить повреждённый файл
sudo rm -f /var/www/teaching_panel/teaching_panel/celerybeat-schedule
sudo rm -f /var/www/teaching_panel/teaching_panel/celerybeat-schedule.db
sudo rm -f /var/www/teaching_panel/teaching_panel/celerybeat-schedule.dir
sudo rm -f /var/www/teaching_panel/teaching_panel/celerybeat-schedule.bak

# 3. Запустить celery-beat (файл пересоздастся автоматически)
sudo systemctl start celery-beat

# 4. Проверить статус
sudo systemctl status celery-beat
```

## Проверка прав

```bash
# Файл должен принадлежать www-data:www-data
ls -la /var/www/teaching_panel/teaching_panel/celerybeat*

# Ожидаемый вывод:
# -rw-r--r-- 1 www-data www-data 16384 ... celerybeat-schedule
```

## Автоматическое исправление

Можно добавить в systemd-сервис:

```ini
# /etc/systemd/system/celery-beat.service
[Service]
ExecStartPre=/bin/rm -f /var/www/teaching_panel/teaching_panel/celerybeat-schedule
```

**Но это не рекомендуется** — потеряется информация о последнем запуске задач, и все периодические задачи выполнятся сразу при старте.

## Профилактика

### 1. Не запускать несколько beat-процессов:

```bash
# Проверить количество процессов
pgrep -af "celery.*beat"

# Должен быть только один!
```

### 2. Правильная остановка сервиса:

```bash
# ✓ Правильно — graceful shutdown
sudo systemctl stop celery-beat

# ✗ Неправильно — может повредить файл
sudo kill -9 $(pgrep -f "celery.*beat")
```

### 3. Использовать DatabaseScheduler вместо shelve (опционально):

```python
# settings.py
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Требует: pip install django-celery-beat
```

## Связь с другими ошибками

Эта ошибка **НЕ связана** с:
- FieldError в send_top_rating_notifications (исправлено отдельно)
- SSL Timeout на localhost (исправлено отдельно)

## FAQ

**Q: Потеряются ли задачи после удаления файла?**
A: Нет. Определения задач хранятся в коде (CELERY_BEAT_SCHEDULE в settings.py). Потеряется только информация о последнем запуске — все задачи выполнятся при следующем наступлении их времени.

**Q: Как часто нужно чистить файл?**
A: Никогда при нормальной работе. Только при возникновении ошибки.

**Q: Можно ли переместить файл в другое место?**
A: Да, через параметр `--schedule`:
```bash
celery -A teaching_panel beat --schedule=/var/run/celery/celerybeat-schedule
```
