# Руководство по ручному деплою на production сервер

## Быстрый деплой (5 минут)

### Шаг 1: Подключение к серверу

```bash
ssh tp
```

### Шаг 2: Обновление кода

```bash
cd /var/www/teaching_panel
sudo -u www-data git pull origin main
```

### Шаг 3: Установка зависимостей

```bash
cd teaching_panel
source ../venv/bin/activate
pip install -r requirements.txt
```

### Шаг 4: Миграции БД

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### Шаг 5: Перезапуск сервисов

```bash
sudo systemctl restart teaching_panel
sudo systemctl restart nginx
# при необходимости:
sudo systemctl restart redis-server celery celery-beat
```

### Шаг 6: Проверка статуса

```bash
sudo systemctl status teaching_panel
sudo systemctl status nginx
sudo journalctl -u teaching_panel -n 50  # Последние 50 логов
```

---

## Полный скрипт (copy-paste)

Скопируйте и вставьте эту команду целиком в терминале после SSH:

```bash
cd /var/www/teaching_panel && \
sudo -u www-data git pull origin main && \
cd teaching_panel && \
source ../venv/bin/activate && \
pip install -r requirements.txt --quiet && \
python manage.py migrate && \
python manage.py collectstatic --noinput && \
sudo systemctl restart teaching_panel && \
sudo systemctl restart nginx && \
echo "✅ Deployment completed!" && \
sudo systemctl status teaching_panel --no-pager | head -10
```

---

## Настройка Google Drive API (первый раз)

### 1. Получение credentials

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте проект или выберите существующий
3. Включите Google Drive API:
   - APIs & Services → Enable APIs and Services
   - Найдите "Google Drive API" и включите
4. Создайте Service Account:
   - APIs & Services → Credentials → Create Credentials → Service Account
   - Заполните название: `teaching-panel-recordings`
   - Роль: `Editor`
5. Создайте ключ:
   - Нажмите на созданный Service Account
   - Keys → Add Key → Create New Key → JSON
   - Скачайте файл `credentials.json`

### 2. Создание папки в Google Drive

1. Откройте [Google Drive](https://drive.google.com/)
2. Создайте папку "Teaching Panel Recordings"
3. Кликните правой кнопкой → Share
4. Добавьте email Service Account (из JSON файла, поле `client_email`)
5. Дайте права Editor
6. Скопируйте ID папки из URL (после `folders/`)
   - Пример: `https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j`
   - ID: `1a2b3c4d5e6f7g8h9i0j`

### 3. Загрузка credentials на сервер

```bash
# На локальной машине (Windows PowerShell)
scp C:\path\to\downloaded-credentials.json tp:/var/www/teaching_panel/gdrive-credentials.json
```

Или вручную:
1. Откройте файл credentials.json в блокноте
2. Скопируйте содержимое
3. На сервере:
   ```bash
   nano /var/www/teaching_panel/gdrive-credentials.json
   # Вставьте содержимое
   # Ctrl+O (сохранить), Enter, Ctrl+X (выход)
   ```

### 4. Настройка переменных окружения

```bash
sudo nano /etc/systemd/system/teaching_panel.service
```

Добавьте в секцию `[Service]`:

```ini
Environment="GDRIVE_CREDENTIALS_FILE=/var/www/teaching_panel/gdrive-credentials.json"
Environment="GDRIVE_RECORDINGS_FOLDER_ID=ваш_id_папки_из_шага_2.6"
Environment="VIDEO_COMPRESSION_ENABLED=1"
```

Сохраните (Ctrl+O, Enter, Ctrl+X).

Перезапустите:

```bash
sudo systemctl daemon-reload
sudo systemctl restart teaching_panel
```

---

## Установка FFmpeg (для сжатия видео)

```bash
sudo apt update
sudo apt install ffmpeg -y
ffmpeg -version  # Проверка
```

---

## Проверка работы системы

### 1. Проверка Google Drive интеграции

```bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell
```

В Python shell:

```python
from schedule.gdrive_utils import get_gdrive_manager

gdrive = get_gdrive_manager()
print("✅ Google Drive connected!")

# Проверка папки
print(f"Root folder ID: {gdrive.root_folder_id}")
```

### 2. Проверка Celery

```bash
sudo systemctl status celery
celery -A teaching_panel inspect active  # Активные задачи
```

### 3. Проверка логов

```bash
# Django logs
sudo journalctl -u teaching_panel -f

# Celery logs
sudo journalctl -u celery -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

---

## Тестирование записей

### 1. Создать урок с записью

1. Войдите как преподаватель
2. Создайте урок
3. Включите чекбокс "Записывать урок"
4. Установите "Доступность записи" (например, 90 дней)
5. Сохраните

### 2. Запуск урока в Zoom

1. Нажмите "Начать урок"
2. Получите ссылку на Zoom встречу
3. Проведите урок с включенной записью

### 3. После завершения

Zoom автоматически:
1. Обработает запись (~5-10 минут)
2. Отправит webhook на `/api/zoom/webhook/`
3. Celery task скачает и загрузит в Google Drive
4. Запись появится в разделе "Записи" для учеников

### 4. Проверка статуса

```bash
# Проверить созданные записи
python manage.py shell
```

В Python shell:

```python
from schedule.models import LessonRecording

recordings = LessonRecording.objects.all()
for rec in recordings:
    print(f"ID: {rec.id}, Status: {rec.status}, Lesson: {rec.lesson.title}")
```

---

## Откат изменений (если что-то сломалось)

```bash
cd /var/www/teaching_panel
sudo -u www-data git log --oneline -10  # Посмотреть последние коммиты
sudo -u www-data git checkout <commit_hash>  # Откатиться на нужный коммит
sudo systemctl restart teaching_panel
sudo systemctl restart nginx
```

---

## Полезные команды

```bash
# Проверка квот хранилища
python manage.py shell -c "from schedule.models import TeacherStorageQuota; [print(f'{q.teacher.email}: {q.used_gb:.2f}/{q.total_gb:.2f} GB') for q in TeacherStorageQuota.objects.all()]"

# Ручной запуск Celery task
python manage.py shell -c "from schedule.tasks import cleanup_old_recordings; cleanup_old_recordings.delay()"

# Очистка кэша Redis
redis-cli FLUSHALL

# Перезапуск всех сервисов
sudo systemctl restart teaching_panel nginx

# Проверка портов
sudo netstat -tulpn | grep LISTEN
```

---

## Контакты для помощи

- **GitHub Issues**: https://github.com/Syrnik1307/nat/issues
- **Documentation**: См. `RECORDINGS_STORAGE_INTERFACE_GUIDE.md`

---

**Last Updated**: 4 декабря 2025
