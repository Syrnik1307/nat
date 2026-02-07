# Fix: RedirectMissingLocation Error

**Дата**: 7 февраля 2026  
**Проблема**: Ошибка `httplib2.error.RedirectMissingLocation` при миграции файлов домашек на Google Drive  
**Sentry Issue**: PYTHON-D3AN60-2C

## Проблема

Google Drive API иногда возвращает HTTP redirect (3xx status) **без Location header**, что вызывает необработанное исключение `RedirectMissingLocation` из библиотеки httplib2. Это происходит при:

- Сетевых проблемах между сервером и Google API
- Нагрузке на Google API infrastructure
- Resumable upload сессиях, прерванных на стороне Google

Текущий код пытался обработать это через `except Exception` и строковый анализ, но это **ненадёжно** - исключение не всегда ловилось корректно.

## Решение

### 1. Явный импорт и обработка RedirectMissingLocation

**Файл**: `schedule/gdrive_utils.py`

```python
# Добавлен явный импорт с fallback
try:
    from httplib2.error import RedirectMissingLocation
except ImportError:
    class RedirectMissingLocation(Exception):
        pass
```

Теперь мы ловим исключение **по его типу**, а не по строке в сообщении.

### 2. Специализированный except блок

**Файл**: `schedule/gdrive_utils.py:_execute_resumable_upload()`

Добавлен отдельный `except RedirectMissingLocation` блок **перед** `except Exception`:

```python
except RedirectMissingLocation as e:
    if retries < MAX_RETRIES:
        retries += 1
        # Сбросить stream (КРИТИЧНО!)
        stream_reset_ok = self._reset_media_stream(media)
        # Пересоздать upload сессию
        request = self.service.files().create(...)
    else:
        logger.error("RedirectMissingLocation persists...")
        raise
```

**Ключевое отличие**: 
- Теперь ловится **строго по типу** (type matching)
- Добавлена проверка успешности сброса stream
- Информативное логирование для debugging

### 3. Улучшенный _reset_media_stream

**Файл**: `schedule/gdrive_utils.py:_reset_media_stream()`

Метод теперь:
- Логирует **текущую позицию** курсора (`tell()` → `seek(0)`)
- Возвращает `bool` (success/failure) для контроля вызывающим кодом
- Различает `MediaIoBaseUpload._fd` vs `MediaFileUpload._file`

```python
def _reset_media_stream(media):
    if hasattr(media, '_fd') and hasattr(media._fd, 'seek'):
        current_pos = media._fd.tell()
        media._fd.seek(0)
        logger.debug(f"Reset media stream cursor: {current_pos} -> 0")
        return True
    # ...
    return False
```

### 4. Fallback на Simple Upload

**Файл**: `schedule/gdrive_utils.py:upload_file()`

Если resumable upload падает с `RedirectMissingLocation` и файл < 5 MB, пробуем простой upload:

```python
try:
    file = self._execute_resumable_upload(...)
except (RedirectMissingLocation, Exception) as e:
    is_redirect_error = isinstance(e, RedirectMissingLocation) or 'redirect' in str(e).lower()
    if is_redirect_error and file_size < SIMPLE_UPLOAD_THRESHOLD:
        logger.warning("Trying simple upload fallback...")
        self._reset_media_stream(media)
        file = self._execute_simple_upload(...)
    else:
        raise
```

### 5. Улучшенное логирование в команде миграции

**Файл**: `homework/management/commands/migrate_homework_files.py`

Теперь различаем типы ошибок:

```python
if 'redirect' in error_msg and 'location' in error_msg:
    # WARNING вместо ERROR - это transient issue
    self.stdout.write(self.style.WARNING(
        f'GDRIVE REDIRECT ERROR (transient) - {e}'
    ))
    logger.warning(...)  # Не логируем exc_info=True для известной transient ошибки
elif 'timeout' in error_msg:
    # ...
else:
    # Неизвестная ошибка - полный traceback
    logger.error(..., exc_info=True)
```

## Ожидаемый эффект

### ✅ До внедрения:
- ❌ RedirectMissingLocation не ловится корректно
- ❌ Падает вся batch миграция
- ❌ Сотни событий в Sentry
- ❌ Stream не сбрасывается → пустые данные при retry

### ✅ После внедрения:
- ✅ Исключение ловится **точно по типу**
- ✅ Автоматический retry с правильным сбросом stream
- ✅ Fallback на simple upload для малых файлов
- ✅ Информативное логирование (WARNING для transient, ERROR для real issues)
- ✅ Меньше ложных срабатываний в Sentry
- ✅ Миграция продолжается даже при единичных redirect errors

## Тестирование

### Локально (dev):

```powershell
# Проверить что код не сломался
cd teaching_panel
python manage.py check

# Попробовать миграцию в dry-run режиме
python manage.py migrate_homework_files --dry-run --batch=5
```

### Production:

```powershell
# Деплой
.\auto_deploy.ps1

# Мониторинг после деплоя
ssh tp "journalctl -u teaching_panel -f"

# Запуск миграции вручную для теста
ssh tp "cd /var/www/teaching_panel && source venv/bin/activate && python manage.py migrate_homework_files --batch=10"

# Проверка Sentry на новые RedirectMissingLocation
# https://sentry.io/issues/PYTHON-D3AN60-2C
```

## Метрики успеха

После деплоя отслеживать:

1. **Sentry**: Количество новых `RedirectMissingLocation` events (должно снизиться до 0)
2. **Logs**: Появление строк `"Resetting stream and creating new upload session"` (успешные retries)
3. **Logs**: Появление строк `"Trying simple upload fallback"` (работает fallback)
4. **Миграция**: Success rate файлов (должен вырасти до ~99%)

## Дополнительные рекомендации

### Если проблема сохраняется:

1. **Проверить версию httplib2**:
   ```bash
   pip show httplib2
   # Должна быть >= 0.20.0
   ```

2. **Увеличить RETRY_DELAY_BASE** в `gdrive_utils.py`:
   ```python
   RETRY_DELAY_BASE = 2.0  # было 1.0
   ```

3. **Уменьшить batch size** миграции:
   ```bash
   # В cron job
   python manage.py migrate_homework_files --batch=10  # было 20
   ```

4. **Добавить backoff между batch runs** (в cron):
   ```bash
   # Вместо */2 минуты → */5 минут
   */5 * * * * cd /var/www/teaching_panel && ...
   ```

## Файлы изменены

- ✅ `teaching_panel/schedule/gdrive_utils.py` (импорт, _execute_resumable_upload, _reset_media_stream, upload_file)
- ✅ `teaching_panel/homework/management/commands/migrate_homework_files.py` (error classification)

## Коммит

```bash
git add teaching_panel/schedule/gdrive_utils.py
git add teaching_panel/homework/management/commands/migrate_homework_files.py
git add REDIRECT_MISSING_LOCATION_FIX.md
git commit -m "fix: proper handling of RedirectMissingLocation in Google Drive uploads

- Add explicit import and except block for httplib2.error.RedirectMissingLocation
- Improve _reset_media_stream with position logging and success return
- Add fallback to simple upload for files <5MB when resumable fails with redirect
- Classify redirect errors as WARNING (transient) vs ERROR (persistent)
- Reduces Sentry noise for known transient Google API issues

Fixes: PYTHON-D3AN60-2C (Sentry)"
```

---

**Автор**: AI Assistant  
**Review**: Требуется
