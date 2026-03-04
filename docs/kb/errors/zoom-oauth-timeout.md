# Zoom OAuth Token Read Timeout

- **Дата**: 2026-01 (периодическая)
- **Severity**: LOW-MEDIUM
- **Компонент**: Zoom Pool / schedule/tasks.py
- **Источник**: @zoom-integration / @prod-monitor

## Симптомы
```
Failed to get Zoom OAuth token: HTTPSConnectionPool(host='zoom.us', port=443): Read timed out. (read timeout=10)
```
Задача `schedule.tasks.warmup_zoom_oauth_tokens` (каждые 55 мин).

## Причина
Таймаут при запросе к Zoom API: временные сетевые проблемы, перегрузка Zoom, DNS (IPv6).

## Решение (уже применено)
1. Увеличен timeout: `timeout=(5, 15)` (connect, read)
2. Retry с backoff: `retry_backoff=60`, `max_retries=2`, `retry_jitter=True`
3. Graceful handling: таймауты не пробрасываются в Sentry, логируются как warning

## Критичность

| Ситуация | Критичность |
|----------|-------------|
| 1-2 таймаута за прогрев | Низкая — retry сработает |
| Все запросы timeout | Средняя — проверить сеть |
| Ошибка при запуске урока | Высокая — токен получится без кеша (~10 сек медленнее) |

Warmup — оптимизация. Без неё токен получается при запуске урока, просто медленнее.
