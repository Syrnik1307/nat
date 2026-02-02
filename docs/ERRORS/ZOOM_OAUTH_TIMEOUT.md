# Ошибка: Zoom OAuth Token Read Timeout

## Симптомы

В Sentry появляется ошибка от задачи `schedule.tasks.warmup_zoom_oauth_tokens`:
```
Failed to get Zoom OAuth token: HTTPSConnectionPool(host='zoom.us', port=443): Read timed out. (read timeout=10)
```

## Причина

Периодическая задача `warmup_zoom_oauth_tokens` прогревает OAuth токены Zoom для всех учителей каждые 55 минут. Таймаут происходит когда:

1. **Сетевые проблемы** — временная недоступность zoom.us с сервера
2. **Zoom API перегружен** — медленный ответ от Zoom OAuth сервера
3. **DNS проблемы** — особенно с IPv6 (мы уже форсируем IPv4)
4. **Слишком много запросов** — если много учителей с Zoom credentials

## Решение (уже применено)

### 1. Увеличен timeout

```python
# Было:
timeout=10

# Стало (connect_timeout, read_timeout):
timeout=(5, 15)
```

### 2. Добавлен retry с backoff

```python
@shared_task(
    name='schedule.tasks.warmup_zoom_oauth_tokens',
    autoretry_for=(Exception,),
    retry_backoff=60,        # Начальная задержка 60 сек
    retry_backoff_max=300,   # Максимум 5 минут
    max_retries=2,           # До 2 повторных попыток
    retry_jitter=True        # Случайный разброс
)
```

### 3. Graceful handling для timeout ошибок

```python
except requests.exceptions.Timeout as e:
    # Не пробрасываем в Sentry, просто логируем warning
    timeout_count += 1
    logger.warning(f"[ZOOM_WARMUP] Timeout for {teacher.email}: {e}")
```

## Мониторинг

Задача теперь возвращает детальную статистику:
```json
{
    "warmed": 5,
    "skipped": 2,
    "timeouts": 1,
    "errors": 0,
    "timestamp": "2026-02-02T02:41:42+00:00"
}
```

## Когда ошибка критична?

| Ситуация | Критичность | Действие |
|----------|-------------|----------|
| 1-2 таймаута за прогрев | Низкая | Игнорировать, retry сработает |
| Все запросы timeout | Средняя | Проверить сеть сервера |
| Ошибка при запуске урока | Высокая | Токен получится без кеша (медленнее) |

## Ручная проверка

```bash
# На сервере — проверить доступность Zoom API
curl -v --connect-timeout 5 --max-time 15 https://zoom.us/oauth/token

# Проверить DNS
dig zoom.us +short

# Проверить IPv6 (должен быть отключен для Zoom)
curl -6 https://zoom.us/oauth/token 2>&1 | head -5
```

## FAQ

**Q: Это влияет на пользователей?**
A: Нет напрямую. Warmup — это оптимизация. Если токен не прогрет, он будет получен при запуске урока (на ~10 сек медленнее).

**Q: Почему retry 2 раза, а не больше?**
A: Задача запускается каждые 55 минут. Если Zoom недоступен долго, лучше дождаться следующего цикла.

**Q: Как отключить warmup?**
A: Удалить задачу из `CELERY_BEAT_SCHEDULE` в settings.py (не рекомендуется).
