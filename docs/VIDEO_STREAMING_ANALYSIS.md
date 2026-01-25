# Анализ проблем стриминга видео из Google Drive

**Дата:** 25 января 2026  
**Статус:** Решено (переход на iframe embed)

---

## Хронология проблем

### 1. Исходная реализация (RecordingPlayer)
- Использовал `streaming_url` → `https://drive.google.com/uc?export=download&id={FILE_ID}`
- **Проблема:** Для файлов >100MB Google показывает страницу подтверждения вирус-сканера
- **Симптом:** Видео не загружалось, `<video>` получал HTML вместо видеопотока

### 2. Серверный прокси (stream_recording endpoint)
Попытка проксировать через Django backend:
```
GET /api/schedule/recordings/{id}/stream/?token={JWT}
```

#### Причины отказа:

| Проблема | Описание | Симптом |
|----------|----------|---------|
| **OAuth прогрев** | Google Drive API требует ~40 сек на первый запрос после рестарта (refresh токена, инициализация) | 504 Gateway Timeout |
| **Nginx таймауты** | `proxy_connect_timeout 60s` был меньше времени инициализации GDrive | 504 Gateway Timeout |
| **JWT в query string** | `<video>` не может отправить Authorization header, токен в URL | 401 при истекшем токене |
| **Нет auto-refresh** | В отличие от axios, `<video src>` не умеет обновлять JWT | "Формат не поддерживается" (получал JSON ошибку) |
| **Gunicorn workers** | 2 воркера, при нагрузке все заняты, новые запросы ждут | Таймаут на первом запросе |

#### Попытки исправления (не помогли полностью):
1. ✅ Увеличили `proxy_connect_timeout` до 300s
2. ✅ Добавили warmup GDrive в `apps.py` при старте
3. ✅ Добавили `ensureFreshAccessToken()` перед установкой video.src
4. ❌ Всё равно первый запрос после рестарта таймаутил

---

## Решение: Google Drive iframe embed

```javascript
const embedUrl = `https://drive.google.com/file/d/${gdrive_file_id}/preview`;
<iframe src={embedUrl} allowFullScreen />
```

### Почему работает:
| Фактор | Прокси | Iframe |
|--------|--------|--------|
| Авторизация | JWT токен в query | Не требуется |
| Инициализация | OAuth прогрев ~40s | Мгновенно |
| Стриминг | Через наш сервер | Напрямую с Google CDN |
| Нагрузка на сервер | Высокая (прокси трафика) | Нулевая |
| Range requests | Надо реализовать | Google делает сам |
| Кэширование | Нет | Google CDN |

---

## Требования к файлам в Google Drive

Для работы iframe embed файлы должны быть доступны по ссылке:
- ✅ "Все, у кого есть ссылка" → "Читатель" (минимум)
- ❌ "Ограниченный доступ" — не будет работать

### Как проверить права:
```python
# В Django shell
from schedule.models import LessonRecording
rec = LessonRecording.objects.get(id=14)
print(rec.gdrive_file_id)
# Открыть: https://drive.google.com/file/d/{FILE_ID}/view
# Если требует входа — права неверные
```

---

## Рекомендации на будущее

### 1. При загрузке записи — сразу делать файл публичным
```python
# В gdrive_utils.py после upload
def make_file_public(file_id):
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }
    service.permissions().create(
        fileId=file_id,
        body=permission
    ).execute()
```

### 2. Если нужен приватный доступ — использовать signed URLs
- Генерировать временные ссылки с `&authuser=0` не работает для iframe
- Альтернатива: перейти на S3/Azure Blob Storage с signed URLs

### 3. Мониторинг
- Добавить метрику "время загрузки GDrive manager" при старте
- Алерт если >30 сек

---

## Когда серверный прокси всё же нужен:

1. **Приватные файлы** — если нельзя делать публичными
2. **Трекинг просмотров** — текущий `/view/` endpoint достаточен
3. **Ограничение скачивания** — iframe не даёт скачать напрямую (только через Google UI)

---

## Файлы затронутые этим анализом:

- `frontend/src/modules/Recordings/FastVideoModal.js` — iframe embed
- `teaching_panel/schedule/views.py` — stream_recording (оставлен как fallback)
- `teaching_panel/schedule/apps.py` — warmup GDrive при старте
- `nginx_fixed_final.conf` — увеличенные таймауты для /stream/

---

## Итог

**Проблема:** Серверный прокси для видео из Google Drive ненадёжен из-за OAuth warmup и таймаутов.

**Решение:** Использовать Google Drive iframe embed (`/preview`) — мгновенно, без нагрузки на сервер.

**Ограничение:** Файлы должны быть публичными (доступ по ссылке).
