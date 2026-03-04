# Dev Environment Agent — Запуск и настройка dev-окружения

## Роль
Ты помогаешь быстро запустить, проверить и отладить локальное окружение разработки Lectio Space.

## Быстрый старт

### Backend
```powershell
cd teaching_panel
..\venv\Scripts\Activate.ps1   # или ..\.venv\Scripts\Activate.ps1
python manage.py runserver
# → http://127.0.0.1:8000
```

### Frontend  
```powershell
cd frontend
npm start
# → http://localhost:3000 (proxy → Django)
```

### Celery (опционально)
```powershell
# Redis (Docker)
docker run -d -p 6379:6379 redis

# Worker
cd teaching_panel
celery -A teaching_panel worker -l info --pool=solo

# Beat
celery -A teaching_panel beat -l info
```

### Без Redis (dev)
Установить в `.env`:
```
USE_IN_MEMORY_CELERY=1
```

## Частые проблемы

### "Invalid response: missing tokens" при логине
Django не запущен или CORS блокирует.
1. Проверить что Django на `http://127.0.0.1:8000`
2. Проверить `frontend/src/setupProxy.js`
3. Network tab → ответ должен быть JSON, не HTML

### ModuleNotFoundError
```powershell
pip install -r requirements.txt
```

### Миграции не применены
```powershell
python manage.py migrate
```

### Нет тестовых данных
```powershell
python manage.py createsuperuser  # admin
python manage.py shell -c "from create_sample_data import run; run()"
```

### Frontend не билдится
```powershell
cd frontend
rm -rf node_modules
npm install
npm run build
```

## Переменные окружения (.env)
```bash
# Минимальный набор для dev:
DEBUG=True
SECRET_KEY=django-insecure-dev-only-key-not-for-production

# Опционально:
ZOOM_ACCOUNT_ID=
ZOOM_CLIENT_ID=
ZOOM_CLIENT_SECRET=
TELEGRAM_BOT_TOKEN=
YOOKASSA_ACCOUNT_ID=  # Без этого → mock payments
```

## Полезные команды
```powershell
# Django shell
python manage.py shell

# Показать все URL'ы
python manage.py show_urls  # нужен django-extensions

# Проверка deployment readiness
python manage.py check --deploy

# Создание миграций
python manage.py makemigrations
python manage.py migrate

# Запуск тестов
python manage.py test
python manage.py test schedule.tests
```
