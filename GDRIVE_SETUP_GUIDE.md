# 🎥 Настройка Google Drive для хранения записей уроков

## 📋 Обзор

Эта система автоматически:
1. ✅ Записывает уроки в Zoom (если включено в настройках)
2. ✅ Скачивает готовые записи с Zoom
3. ✅ Загружает в ваш Google Drive (2TB)
4. ✅ Удаляет запись с Zoom (освобождает место)
5. ✅ Предоставляет ученикам доступ к просмотру

---

## 🔧 Шаг 1: Создание Service Account в Google Cloud

### 1.1 Перейдите в Google Cloud Console
👉 https://console.cloud.google.com/

### 1.2 Создайте новый проект
- Нажмите "Select a project" → "New Project"
- Название: `Teaching Panel Recordings`
- Нажмите "Create"

### 1.3 Включите Google Drive API
1. Перейдите в "APIs & Services" → "Enable APIs and Services"
2. Найдите "Google Drive API"
3. Нажмите "Enable"

### 1.4 Создайте Service Account
1. "APIs & Services" → "Credentials"
2. "Create Credentials" → "Service Account"
3. Заполните:
   - Name: `teaching-panel-drive`
   - Description: `Service account for automatic recording uploads`
4. Нажмите "Create and Continue"
5. Role: `Editor` (или создайте custom роль с доступом только к Drive)
6. Нажмите "Done"

### 1.5 Создайте ключ (credentials.json)
1. Найдите созданный Service Account в списке
2. Кликните на email Service Account
3. Вкладка "Keys" → "Add Key" → "Create new key"
4. Тип: **JSON**
5. Нажмите "Create"
6. **Сохраните файл как `gdrive-credentials.json`**

---

## 📁 Шаг 2: Создание папки в Google Drive

### 2.1 Откройте свой Google Drive
👉 https://drive.google.com/

### 2.2 Создайте папку для записей
1. Правый клик → "New folder"
2. Название: `Teaching Panel Recordings`
3. Внутри создайте подпапки (опционально):
   ```
   Teaching Panel Recordings/
   ├── 2025/
   │   ├── January/
   │   ├── February/
   │   └── ...
   ```

### 2.3 Поделитесь папкой с Service Account
1. Правый клик на папку "Teaching Panel Recordings" → "Share"
2. Вставьте email вашего Service Account (из шага 1.4)
   - Пример: `teaching-panel-drive@your-project.iam.gserviceaccount.com`
3. Права: **Editor** (чтобы загружать и удалять файлы)
4. Нажмите "Share"

### 2.4 Скопируйте Folder ID
1. Откройте папку "Teaching Panel Recordings"
2. URL выглядит так: `https://drive.google.com/drive/folders/XXXXXXXXXXXXXXXXXXXXX`
3. **Скопируйте ID** (часть после `/folders/`)
   - Пример: `1a2B3c4D5e6F7g8H9i0J`

---

## ⚙️ Шаг 3: Настройка на сервере

### 3.1 Загрузите credentials на сервер

```bash
# На вашем компьютере
scp gdrive-credentials.json root@72.56.81.163:/var/www/teaching_panel/

# На сервере
cd /var/www/teaching_panel/
chmod 600 gdrive-credentials.json
chown www-data:www-data gdrive-credentials.json
```

### 3.2 Обновите settings.py

```python
# teaching_panel/teaching_panel/settings.py

# Google Drive настройки
GDRIVE_CREDENTIALS_FILE = os.path.join(BASE_DIR, 'gdrive-credentials.json')
GDRIVE_RECORDINGS_FOLDER_ID = '1a2B3c4D5e6F7g8H9i0J'  # Ваш Folder ID из шага 2.4
```

### 3.3 Установите зависимости

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Или добавьте в `requirements.txt`:
```
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.110.0
```

---

## 🧪 Шаг 4: Тестирование

### 4.1 Проверьте подключение

```bash
cd /var/www/teaching_panel/
python manage.py shell
```

```python
from schedule.gdrive_utils import get_gdrive_manager

# Инициализация
gdrive = get_gdrive_manager()

# Создать тестовую папку
folder_id = gdrive.create_folder("Test Folder")
print(f"Created folder: {folder_id}")

# Загрузить тестовый файл (создайте test.txt)
with open('test.txt', 'w') as f:
    f.write('Hello from Teaching Panel!')

result = gdrive.upload_file(
    file_path='test.txt',
    file_name='test-upload.txt',
    mime_type='text/plain'
)

print(f"Uploaded file: {result}")
print(f"View link: {result['web_view_link']}")

# Удалить тестовые данные
gdrive.delete_file(result['file_id'])
gdrive.delete_file(folder_id)
```

✅ Если все работает — увидите ссылки на файлы в Google Drive!

---

## 🔐 Безопасность

### Важно:
- ❌ **НЕ коммитьте** `gdrive-credentials.json` в Git!
- ✅ Добавьте в `.gitignore`:
  ```
  gdrive-credentials.json
  *-credentials.json
  ```
- ✅ Храните резервную копию credentials в безопасном месте (1Password, Bitwarden)
- ✅ Периодически ротируйте ключи (каждые 90 дней)

---

## 📊 Мониторинг использования Google Drive

### Проверка занятого места:
1. Откройте https://drive.google.com/settings/storage
2. Посмотрите сколько используется из 2TB

### Оценка потребления:
```
Zoom запись: ~300 MB/час
20 уроков/день × 300 MB = 6 GB/день
6 GB × 30 дней = 180 GB/месяц
180 GB × 11 месяцев = ~2 TB/год ✅
```

👉 У вас хватит места на **~1 год** записей при активной работе!

### Автоматическая очистка старых записей:
Через 90 дней (настраивается в `Lesson.recording_available_for_days`) записи автоматически удаляются из Google Drive.

---

## 🚀 Готово!

Теперь система полностью настроена:
- ✅ Zoom → автоматическая запись
- ✅ Запись → скачивание в фоне
- ✅ Загрузка в Google Drive
- ✅ Доступ ученикам через веб-плеер
- ✅ Автоудаление старых записей

### Следующие шаги:
1. Создайте миграции БД: `python manage.py makemigrations`
2. Примените миграции: `python manage.py migrate`
3. Настройте Zoom Webhooks (следующий файл)
4. Запустите фоновые задачи (Django-Q)

---

## 🆘 Troubleshooting

### Ошибка "Credentials not found"
- Проверьте путь в settings.py
- Проверьте права доступа: `chmod 600 gdrive-credentials.json`

### Ошибка "403 Forbidden"
- Убедитесь что Service Account добавлен в папку Google Drive (шаг 2.3)
- Проверьте что Drive API включен (шаг 1.3)

### Файлы не загружаются
- Проверьте логи: `/var/log/teaching_panel/django.log`
- Проверьте что Django-Q worker запущен: `systemctl status django-q`

### Вопросы?
Пишите в чат — помогу настроить! 🚀
