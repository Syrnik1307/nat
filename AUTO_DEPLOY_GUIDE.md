# 🚀 АВТОМАТИЧЕСКИЙ ДЕПЛОЙ - QUICK START

## ✅ Готово к запуску

У вас есть полностью автоматизированный скрипт деплоя! Он сделает всё за вас.

## 📋 Что делает скрипт автоматически:

1. ✅ Устанавливает все зависимости (Python, PostgreSQL, Redis, Nginx)
2. ✅ Создаёт виртуальное окружение
3. ✅ Устанавливает Python пакеты
4. ✅ Настраивает базу данных и применяет миграции
5. ✅ Собирает статику Django
6. ✅ Билдит React фронтенд
7. ✅ Настраивает systemd сервисы (Gunicorn, Celery)
8. ✅ Настраивает Nginx с вашим доменом
9. ✅ Получает SSL сертификат (Let's Encrypt)
10. ✅ Запускает все сервисы

## 🎯 Пошаговая инструкция

### Шаг 1: Подготовить .env файл (НА СЕРВЕРЕ)

```bash
# Скопировать .env.example
cp teaching_panel/.env.example teaching_panel/.env

# Отредактировать
nano teaching_panel/.env
```

**ОБЯЗАТЕЛЬНО изменить:**
```bash
# Сгенерировать новый SECRET_KEY (или скрипт сделает это сам)
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

SECRET_KEY=ваш-новый-секретный-ключ
DEBUG=False
ALLOWED_HOSTS=ваш-домен.com,www.ваш-домен.com,72.56.81.163

# PostgreSQL (скрипт попросит создать БД)
DATABASE_URL=postgresql://teaching_user:secure_password@localhost:5432/teaching_panel_db

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
DEFAULT_FROM_EMAIL=noreply@your-domain.com

# Домен
FRONTEND_URL=https://ваш-домен.com
SERVER_HOST=ваш-домен.com

# reCAPTCHA (опционально, скрипт использует тестовые ключи по умолчанию)
RECAPTCHA_PUBLIC_KEY=ваш-публичный-ключ
RECAPTCHA_PRIVATE_KEY=ваш-приватный-ключ

# Zoom API (опционально)
ZOOM_ACCOUNT_ID=ваш-zoom-account-id
ZOOM_CLIENT_ID=ваш-zoom-client-id
ZOOM_CLIENT_SECRET=ваш-zoom-client-secret
```

### Шаг 2: Скопировать проект на сервер

```bash
# НА ВАШЕМ КОМПЬЮТЕРЕ (из директории nat/)
scp -r teaching_panel frontend root@ваш-сервер-ip:/root/
```

Или через Git:
```bash
# НА СЕРВЕРЕ
cd /root
git clone https://github.com/Syrnik1307/nat.git
cd nat
```

### Шаг 3: Запустить автоматический деплой

```bash
# НА СЕРВЕРЕ
cd /root/teaching_panel/deployment  # или /root/nat/teaching_panel/deployment

# Сделать скрипт исполняемым
chmod +x deploy.sh

# ЗАПУСТИТЬ ДЕПЛОЙ
sudo bash deploy.sh
```

### Шаг 4: Следовать подсказкам скрипта

Скрипт интерактивный, он спросит:

1. **Домен:** Введите ваш домен (например: `teachingpanel.ru`)
2. **Создать суперпользователя?** (y/n) - введите `y` чтобы создать админа
3. **Получить SSL сертификат?** (y/n) - введите `y` для HTTPS

### Шаг 5: Создать БД вручную (если нужно)

Если скрипт попросит создать БД:

```bash
# Войти в PostgreSQL
sudo -u postgres psql

# Создать БД и пользователя
CREATE DATABASE teaching_panel_db;
CREATE USER teaching_user WITH PASSWORD 'secure_password';
ALTER ROLE teaching_user SET client_encoding TO 'utf8';
ALTER ROLE teaching_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE teaching_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE teaching_panel_db TO teaching_user;
\q

# Продолжить деплой
sudo bash deploy.sh
```

## ✅ После успешного деплоя

Скрипт покажет:
```
✅ Deployment completed successfully!
✅ Your application is now running at:
   https://ваш-домен.com

✅ Service management commands:
   sudo systemctl status teaching_panel
   sudo systemctl restart teaching_panel
   sudo systemctl logs -u teaching_panel -f
```

### Проверить что всё работает:

1. **Открыть сайт:** `https://ваш-домен.com`
2. **Админка:** `https://ваш-домен.com/admin`
3. **API:** `https://ваш-домен.com/api/`

### Посмотреть логи:

```bash
# Django/Gunicorn логи
sudo journalctl -u teaching_panel -f

# Celery логи
sudo journalctl -u celery -f

# Nginx логи
sudo tail -f /var/log/nginx/teaching_panel_access.log
sudo tail -f /var/log/nginx/teaching_panel_error.log

# Django application логи
sudo tail -f /var/log/teaching_panel/django.log
sudo tail -f /var/log/teaching_panel/requests.log
```

### Управление сервисами:

```bash
# Перезапустить Django
sudo systemctl restart teaching_panel

# Перезапустить Celery
sudo systemctl restart celery
sudo systemctl restart celery-beat

# Перезапустить Nginx
sudo systemctl restart nginx

# Посмотреть статус всех сервисов
sudo systemctl status teaching_panel celery celery-beat nginx redis-server
```

## 🔧 Если что-то пошло не так

### Проблема: "Permission denied"
```bash
sudo chmod +x deployment/deploy.sh
sudo bash deployment/deploy.sh
```

### Проблема: "PostgreSQL connection failed"
Проверьте DATABASE_URL в .env и создайте БД вручную (см. Шаг 5)

### Проблема: "Port 80 already in use"
```bash
# Остановить другие веб-серверы
sudo systemctl stop apache2
sudo killall nginx
sudo bash deployment/deploy.sh
```

### Проблема: "SSL certificate failed"
```bash
# Убедитесь что DNS записи настроены
# A запись: ваш-домен.com → IP сервера
# Проверить:
nslookup ваш-домен.com

# Попробовать ещё раз
sudo certbot --nginx -d ваш-домен.com -d www.ваш-домен.com
```

### Проблема: "Frontend не собирается"
```bash
# Установить Node.js вручную
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Собрать фронтенд
cd /var/www/teaching_panel/frontend
npm install
npm run build
```

## 🎉 Готово!

После успешного деплоя ваш проект будет доступен по адресу `https://ваш-домен.com`

**Важно:**
- Все сервисы запускаются автоматически при перезагрузке сервера
- Логи ротируются автоматически (хранятся 14 дней)
- SSL сертификат обновляется автоматически (Let's Encrypt)

**Полезные ссылки:**
- Админка: `https://ваш-домен.com/admin`
- API docs: `https://ваш-домен.com/api/`
- Статика: `https://ваш-домен.com/static/`

## 📚 Дополнительная документация

- `DEPLOYMENT_GUIDE.md` - подробное руководство
- `PRE_DEPLOYMENT_CHECKLIST.md` - чеклист перед деплоем
- `PRODUCTION_CHECKLIST.md` - чеклист production настроек
- `.env.example` - пример переменных окружения
