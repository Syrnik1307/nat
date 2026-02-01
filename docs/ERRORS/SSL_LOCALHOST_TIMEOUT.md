# Ошибка: ReadTimeout / SSL Handshake Timeout на localhost

## Симптомы

В Sentry появляется ошибка:
```
ReadTimeout: HTTPSConnectionPool(host='127.0.0.1', port=8000): Read timed out. (read timeout=5)
timeout: _ssl.c:1128: The handshake operation timed out
```

**Stack trace указывает на**: `/tmp/test_prod.py` или похожий временный скрипт.

## Причина

Какой-то тестовый скрипт пытается делать **HTTPS**-запрос к `127.0.0.1:8000`, но:
- Gunicorn/Django слушает на **HTTP** (не HTTPS) на порту 8000
- SSL handshake зависает, потому что сервер не понимает TLS

### Типичные источники проблемы:

1. **Временный тестовый скрипт** — кто-то вручную создал `/tmp/test_prod.py`
2. **Неправильный URL в коде** — использование `https://127.0.0.1:8000` вместо `http://`
3. **CI/CD smoke test** — скрипт проверки здоровья с неправильным протоколом

## Быстрое исправление

```bash
# 1. Найти и удалить временный скрипт
rm -f /tmp/test_prod.py

# 2. Проверить, нет ли других подозрительных скриптов
ls -la /tmp/*.py

# 3. Если проблема повторяется, найти источник
grep -r "https://127.0.0.1:8000" /var/www/teaching-panel/
grep -r "https://localhost:8000" /var/www/teaching-panel/
```

## Автоматическая диагностика

Запустите скрипт `scripts/fix_ssl_localhost.sh` на сервере:

```bash
cd /var/www/teaching-panel
./scripts/fix_ssl_localhost.sh
```

## Профилактика

### Правило для тестовых скриптов:

```python
# ✗ НЕПРАВИЛЬНО - HTTPS к локальному серверу
requests.get("https://127.0.0.1:8000/api/me/")

# ✓ ПРАВИЛЬНО - HTTP к локальному серверу  
requests.get("http://127.0.0.1:8000/api/me/")

# ✓ ЕЩЁ ЛУЧШЕ - использовать переменную окружения
import os
BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
requests.get(f"{BASE_URL}/api/me/")
```

### Проверка в CI/CD:

Добавьте в pre-commit hook:
```bash
# Запретить https://127.0.0.1 и https://localhost
if grep -rn "https://127\.0\.0\.1\|https://localhost" --include="*.py" .; then
    echo "ERROR: Found HTTPS to localhost - use HTTP instead"
    exit 1
fi
```

## Связанные файлы

- [fix_ssl_localhost.sh](scripts/fix_ssl_localhost.sh) — автоматическое исправление
- [debug_celery_tasks.py](debug_celery_tasks.py) — диагностика Celery (не связано напрямую)

## FAQ

**Q: Почему ошибка появляется в Sentry?**
A: Sentry SDK перехватывает все необработанные исключения. Временный скрипт выбросил исключение и Sentry его залогировал.

**Q: Это влияет на пользователей?**
A: Нет. Это ошибка в изолированном тестовом скрипте, не в основном приложении.

**Q: Нужно ли перезапускать сервисы?**
A: Нет. Просто удалите проблемный скрипт.
