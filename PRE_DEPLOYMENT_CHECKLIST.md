# ✅ PRE-DEPLOYMENT CHECKLIST

## 🔍 Что проверено

### ✅ Frontend - Все hardcoded URL исправлены
- ✅ `ChatList.js` - использует `/api/` вместо `http://localhost:8000`
- ✅ `ChatThread.js` - использует `/api/` вместо `http://localhost:8000`
- ✅ `GroupChatModal.js` - использует `/api/` вместо `http://localhost:8000`
- ✅ `EmailVerificationPage.js` - использует `/api/` вместо `http://localhost:8000`
- ✅ `apiService.js` - использует относительные пути `/api/`
- ℹ️ `setupProxy.js` - только для dev, в production не используется

### ✅ Backend - Всё через переменные окружения
- ✅ `DEBUG` - через `os.environ.get('DEBUG', 'True')`
- ✅ `SECRET_KEY` - через `os.environ.get('SECRET_KEY')`
- ✅ `ALLOWED_HOSTS` - через `os.environ.get('ALLOWED_HOSTS')`
- ✅ `DATABASE_URL` - через `dj-database-url`
- ✅ `REDIS_URL` - через `os.environ.get('REDIS_URL')`
- ✅ `CELERY_BROKER_URL` - через переменные окружения
- ✅ `CORS_ALLOWED_ORIGINS` - динамические через `SERVER_HOST` + `CORS_EXTRA`
- ✅ `FRONTEND_URL` - через `os.environ.get('FRONTEND_URL')`
- ✅ `EMAIL_HOST/PORT/USER/PASSWORD` - через переменные окружения
- ✅ `RECAPTCHA_PUBLIC_KEY/PRIVATE_KEY` - через переменные окружения
- ✅ `SENTRY_DSN` - через переменные окружения (опционально)

### ✅ Тестовые файлы (НЕ попадут в production)
- ℹ️ `test_*.py` - только для локальной разработки
- ℹ️ `locustfile.py` - для нагрузочного тестирования
- ℹ️ `create_load_test_users.py` - для генерации тестовых данных

## 📋 Что нужно сделать ПЕРЕД деплоем

### 1. Создать .env файл на сервере
```bash
cd /path/to/teaching_panel
cp .env.example .env
nano .env
```

**ОБЯЗАТЕЛЬНО изменить:**
```bash
# Генерируем новый SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# В .env:
SECRET_KEY=ваш-сгенерированный-ключ
DEBUG=False
ALLOWED_HOSTS=ваш-домен.com,www.ваш-домен.com,72.56.81.163
DATABASE_URL=postgresql://user:password@localhost:5432/teaching_panel_db
FRONTEND_URL=https://ваш-домен.com
SERVER_HOST=ваш-домен.com
```

### 2. Настроить PostgreSQL
```bash
sudo -u postgres psql
CREATE DATABASE teaching_panel_db;
CREATE USER teaching_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE teaching_panel_db TO teaching_user;
\q
```

### 3. Настроить Redis
```bash
sudo apt-get install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 4. Установить зависимости
```bash
cd /path/to/teaching_panel
pip install -r requirements.txt
```

### 5. Применить миграции
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 6. Создать суперпользователя
```bash
python manage.py createsuperuser
```

### 7. Настроить Gunicorn + Nginx
Следуйте инструкциям в `DEPLOYMENT_GUIDE.md`

### 8. Настроить SSL (Let's Encrypt)
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d ваш-домен.com -d www.ваш-домен.com
```

### 9. Запустить Celery workers
```bash
celery -A teaching_panel worker -l info --detach
celery -A teaching_panel beat -l info --detach
```

### 10. Настроить email (Gmail App Password)
1. Зайдите в Google Account → Security
2. Включите 2FA
3. Создайте App Password
4. Добавьте в .env:
```bash
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-digit-app-password
```

## 🚫 Что НЕ нужно делать

❌ **НЕ** включайте в production:
- `DEBUG=True`
- Default `SECRET_KEY`
- SQLite базу данных (только PostgreSQL/MySQL)
- `ALLOWED_HOSTS=*`
- HTTP без SSL (только HTTPS)

❌ **НЕ** коммитьте в git:
- `.env` файл
- `db.sqlite3`
- `logs/*.log`
- `media/` папку с загруженными файлами
- `__pycache__/` и `*.pyc` файлы

## ✅ После деплоя проверить

1. **Сайт открывается:**
   - `https://ваш-домен.com` - фронтенд
   - `https://ваш-домен.com/admin` - админка Django

2. **API работает:**
   - `https://ваш-домен.com/api/jwt/token/` - POST (логин)
   - `https://ваш-домен.com/api/homework/` - GET (список ДЗ)

3. **Email отправляются:**
   - Зарегистрируйте тестового пользователя
   - Проверьте приход письма верификации

4. **Celery работает:**
   ```bash
   # Проверить запущенные процессы
   ps aux | grep celery
   
   # Проверить логи
   tail -f /path/to/celery.log
   ```

5. **Логи пишутся:**
   ```bash
   tail -f teaching_panel/logs/django.log
   tail -f teaching_panel/logs/requests.log
   ```

6. **Мониторинг Sentry:**
   - Проверьте что ошибки попадают в Sentry (если настроен)

## 🔥 Быстрый деплой (если всё готово)

```bash
# 1. Скопировать код на сервер
scp -r teaching_panel/* user@server:/var/www/teaching_panel/

# 2. SSH на сервер
ssh user@server

# 3. Создать .env
cd /var/www/teaching_panel
cp .env.example .env
nano .env  # заполнить реальные значения

# 4. Установить зависимости
source venv/bin/activate
pip install -r requirements.txt

# 5. Миграции
python manage.py migrate
python manage.py collectstatic --noinput

# 6. Перезапустить сервисы
sudo systemctl restart gunicorn
sudo systemctl restart nginx
sudo systemctl restart celery-worker
```

## 📚 Дополнительные ресурсы

- `DEPLOYMENT_GUIDE.md` - полная инструкция по деплою
- `LOAD_TESTING_GUIDE.md` - как протестировать нагрузку
- `TEACHER_REVIEW_FEATURE.md` - документация системы проверки ДЗ
- `.env.example` - пример всех переменных окружения

## ✅ Готово!

Все hardcoded localhost URL убраны, всё настраивается через .env. Система готова к деплою на production сервер! 🚀
