# Оптимизация для VPS 2GB RAM

- **Тип**: Архитектурный паттерн
- **Компоненты**: Gunicorn, Celery, Nginx, systemd

## Бюджет памяти

| Компонент | Limit | Примечание |
|-----------|-------|------------|
| Gunicorn | 2 workers, gthread | max-requests=1000, max-requests-jitter=50 |
| Celery worker | 1, concurrency=1 | MAX_TASKS_PER_CHILD=50, MAX_MEMORY=150MB |
| Celery beat | 1 | Минимальный footprint |
| Nginx | default | worker_connections 512 |
| Redis | default | maxmemory 64mb |
| Swap | 2GB | Обязательно |

## Ключевые настройки

### Gunicorn (gunicorn.conf.py)
```python
workers = 2
worker_class = "gthread"
threads = 4
max_requests = 1000
max_requests_jitter = 50
```

### Celery (settings.py)
```python
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 150000  # 150MB
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
```

### systemd
```ini
MemoryMax=600M  # Не ниже!
MemoryHigh=500M
```

## Мониторинг
```bash
free -h                          # Общая память
ps aux --sort=-%mem | head -10   # Топ процессы
journalctl -k | grep -i oom     # OOM события
```
