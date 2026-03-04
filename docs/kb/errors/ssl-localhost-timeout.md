# SSL/HTTPS Timeout на localhost

- **Дата**: 2026-01
- **Severity**: LOW
- **Компонент**: Тестовые скрипты
- **Источник**: @dev-environment

## Симптомы
```
ReadTimeout: HTTPSConnectionPool(host='127.0.0.1', port=8000): Read timed out.
timeout: _ssl.c:1128: The handshake operation timed out
```

## Причина
Тестовый скрипт делает HTTPS-запрос к `127.0.0.1:8000`, но Gunicorn/Django слушает HTTP.
SSL handshake зависает. Типичный источник — временный `/tmp/test_prod.py`.

## Решение
```bash
rm -f /tmp/test_prod.py
ls -la /tmp/*.py
grep -r "https://127.0.0.1:8000" /var/www/teaching-panel/
```

## Правило
```python
# НЕПРАВИЛЬНО
requests.get("https://127.0.0.1:8000/api/me/")

# ПРАВИЛЬНО
requests.get("http://127.0.0.1:8000/api/me/")
```

Не влияет на пользователей — ошибка в изолированном тестовом скрипте.
