# Gunicorn Worker SIGKILL (OOM)

- **Дата**: 2026-01 (повторяющаяся)
- **Severity**: SEV1
- **Компонент**: Gunicorn / Production Server
- **Источник**: @prod-monitor / @performance-optimizer

## Симптомы
```
Worker (pid:689792) was sent SIGKILL! Perhaps out of memory?
```

## Причина
Linux OOM Killer убивает процесс при нехватке RAM (сервер 2GB).
Слишком много workers, дублирующие сервисы, низкий MemoryMax, утечки памяти.

## Оптимальная конфигурация для 2GB RAM

| Компонент | Процессы | RAM |
|-----------|----------|-----|
| Gunicorn master | 1 | ~50 МБ |
| Gunicorn workers | 2 | ~180 МБ |
| Celery worker | 1 | ~100 МБ |
| Celery beat | 1 | ~100 МБ |
| **Итого** | 5 | **~430 МБ** |

## Решение
```bash
sudo systemctl stop celery_worker celery_beat celery-combined 2>/dev/null
sudo systemctl disable celery_worker celery_beat celery-combined 2>/dev/null
sudo pkill -f celery
sudo sed -i 's/--workers 3/--workers 2/' /etc/systemd/system/teaching_panel.service
sudo systemctl daemon-reload
sudo systemctl restart teaching_panel celery celery-beat
```

## Профилактика
- Включить swap (2 ГБ): `sudo fallocate -l 2G /swapfile`
- `max-requests` для автоперезапуска workers
- `MemoryMax` не ниже 600M в systemd unit
- Один celery worker с `--concurrency=1`

## Связь
- См. также: [celerybeat-schedule-corruption.md](celerybeat-schedule-corruption.md) — OOM может повредить shelve
