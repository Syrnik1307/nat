# Emergency: Восстановление изображений ДЗ

## Быстрый старт (на сервере)

### 1. Диагностика конкретного ДЗ

```bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

# Найти ДЗ для группы "Информатика 1" от 14 декабря
python ../diagnose_and_restore_hw_images.py --diagnose --group "Информатика" --date 2024-12-14

# Или по конкретному homework_id
python ../diagnose_and_restore_hw_images.py --diagnose --homework-id 42 -v
```

### 2. Восстановление с бэкапом

```bash
# Сначала ВСЕГДА делаем dry-run
python ../diagnose_and_restore_hw_images.py --restore --dry-run --group "Информатика"

# Если всё ОК — запускаем с бэкапом
python ../diagnose_and_restore_hw_images.py --restore --backup --group "Информатика"
```

### 3. Проверка результата

```bash
# Повторная диагностика — должно быть 0 проблем
python ../diagnose_and_restore_hw_images.py --diagnose --homework-id 42
```

---

## Типы проблем и решения

| Проблема | Причина | Решение |
|----------|---------|---------|
| `GDRIVE_FILE_MISSING_OR_TRASHED` | Файл удалён cleanup-скриптом | Скрипт ищет в корзине и восстанавливает |
| `LOCAL_FILE_MISSING` | Локальный файл удалён, GDrive есть | Скрипт переключает storage на GDrive |
| `HOMEWORK_FILE_NOT_FOUND` | HomeworkFile запись отсутствует | Нужно найти файл вручную и создать запись |
| `GDRIVE_URL_INVALID` | Некорректный URL | Нужно найти правильный gdrive_file_id |

---

## Профилактика

### Заблокированные скрипты

Эти скрипты **ОТКЛЮЧЕНЫ** — они удаляли файлы ДЗ:
- `cleanup_lectio_folders.py` ⛔
- `cleanup_teacher_folders.py` ⛔

### Безопасные альтернативы

Используйте эти скрипты вместо старых:
```bash
# Проверяет HomeworkFile перед удалением
python safe_cleanup_gdrive.py --dry-run

# Проверяет подписки + HomeworkFile
python cleanup_old_gdrive_folders.py  # dry_run=True по умолчанию
```

---

## Ручное восстановление из корзины GDrive

Если скрипт не нашёл файлы, проверьте корзину вручную:

```python
# Django shell
from schedule.gdrive_utils import get_gdrive_manager
gdrive = get_gdrive_manager()

# Поиск в корзине по имени
filename = "homework_teacher4_1768412910_92cffb0b_image.png"
query = f"name='{filename}' and trashed=true"
res = gdrive.service.files().list(
    q=query,
    spaces='drive',
    corpora='allDrives',
    includeItemsFromAllDrives=True,
    supportsAllDrives=True,
    fields='files(id, name, trashed)'
).execute()
print(res.get('files', []))

# Восстановление файла
file_id = "..."
gdrive.service.files().update(
    fileId=file_id,
    body={'trashed': False},
    supportsAllDrives=True
).execute()
```

---

## Контакты

При возникновении проблем см. [RCA_HOMEWORK_IMAGES_LOSS.md](RCA_HOMEWORK_IMAGES_LOSS.md)
