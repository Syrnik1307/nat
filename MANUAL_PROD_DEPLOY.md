# 📋 Ручной Деплой Teaching Panel на Production (БЕЗ ПАРОЛЯ)

**Дата**: 5 декабря 2025  
**Версия**: 1.0  
**Статус**: ✅ Готово к развертыванию

---

## 🚀 БЫСТРЫЙ ДЕПЛОЙ (копируй и вставляй целиком)

### Если у тебя настроен SSH alias `tp`

Просто скопируй эту одну команду и вставь в терминал:

```bash
ssh tp "cd /var/www/teaching_panel && sudo -u www-data git pull origin main && cd teaching_panel && source ../venv/bin/activate && pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput && sudo systemctl restart teaching_panel && sudo systemctl restart nginx && echo '✅ Деплой завершен!' && sudo systemctl status teaching_panel --no-pager"
```

**Что происходит:**
1. Подключается к серверу
2. Тянет код из гита (main ветка)
3. Устанавливает зависимости
4. Запускает миграции БД
5. Собирает статические файлы
6. Перезапускает сервисы
7. Проверяет статус

---

## 📱 ПОШАГОВО (если что-то не работает)

### Шаг 1️⃣ Подключение к серверу

```bash
ssh tp
```

Или если alias не настроен:

```bash
ssh user@your-server-ip
```

### Шаг 2️⃣ Переход в папку проекта

```bash
cd /var/www/teaching_panel
```

### Шаг 3️⃣ Обновление кода из Git

```bash
sudo -u www-data git pull origin main
```

**Что будет:**
```
From https://github.com/Syrnik1307/nat
 * branch            main       -> FETCH_HEAD
Already up to date.
# или новые файлы будут скачаны
```

### Шаг 4️⃣ Установка зависимостей

```bash
cd teaching_panel
source ../venv/bin/activate
pip install -r requirements.txt
```

**Что будет:**
```
Collecting django==5.2
...
Successfully installed django-5.2
```

### Шаг 5️⃣ Миграции БД

```bash
python manage.py migrate
```

**Что будет:**
```
Running migrations:
  Applying accounts.0001_initial... OK
  Applying core.0001_initial... OK
...
```

### Шаг 6️⃣ Сбор статических файлов

```bash
python manage.py collectstatic --noinput
```

**Что будет:**
```
123 static files copied to '/var/www/teaching_panel/static', 0 unmodified, 0 post-processed.
```

### Шаг 7️⃣ Перезапуск сервисов

```bash
# Основной сервис Django
sudo systemctl restart teaching_panel

# Веб-сервер
sudo systemctl restart nginx

# (опционально) Celery и Redis
sudo systemctl restart redis-server celery celery-beat
```

### Шаг 8️⃣ Проверка статуса

```bash
sudo systemctl status teaching_panel
sudo systemctl status nginx
```

**Что должно быть:**
```
● teaching_panel.service - Django Teaching Panel
     Loaded: loaded (/etc/systemd/system/teaching_panel.service; enabled; vendor preset: enabled)
     Active: active (running) since ... ago
```

---

## 🐛 РЕШЕНИЕ ПРОБЛЕМ

### ❌ Проблема: `git pull` требует пароль

**Решение:** Используй SSH ключи вместо HTTPS
```bash
# Проверь что используется SSH
git remote -v

# Если там https://, измени на SSH
git remote set-url origin git@github.com:Syrnik1307/nat.git
```

### ❌ Проблема: `pip install` медленный

**Решение:** Пропусти установку если нет изменений
```bash
# Только если requirements.txt изменился
git diff HEAD~1 requirements.txt
```

### ❌ Проблема: Permission denied на collectstatic

**Решение:** Измени права папки
```bash
sudo chown -R www-data:www-data /var/www/teaching_panel
```

### ❌ Проблема: Teaching Panel service не запускается

**Решение:** Проверь логи
```bash
sudo journalctl -u teaching_panel -n 50
```

---

## 📊 ПРОВЕРКА СТАТУСА ПОСЛЕ ДЕПЛОЯ

Выполни эти команды чтобы убедиться что всё работает:

```bash
# 1. Статус сервис
sudo systemctl status teaching_panel --no-pager

# 2. Статус Nginx
sudo systemctl status nginx --no-pager

# 3. Последние логи (последние 20 строк)
sudo journalctl -u teaching_panel -n 20

# 4. Проверка что API отвечает
curl http://localhost:8000/api/me/

# 5. Проверка на ошибки миграций
python manage.py migrate --check
```

---

## 🔧 ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ

Перед первым деплоем убедись что на сервере есть `.env` файл:

```bash
# Проверь что файл существует
ls -la /var/www/teaching_panel/teaching_panel/.env

# Если нет, создай его:
# Основные переменные
DEBUG=False
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# БД (если не SQLite)
DATABASE_URL=postgresql://user:pass@localhost:5432/teaching_panel

# Zoom API
ZOOM_ACCOUNT_ID=your-zoom-account-id
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret

# YooKassa (платежи)
YOOKASSA_ACCOUNT_ID=your-account-id
YOOKASSA_SECRET_KEY=your-secret-key
YOOKASSA_WEBHOOK_SECRET=your-webhook-secret

# Google Drive (записи)
GOOGLE_DRIVE_FOLDER_ID=your-folder-id
GOOGLE_CREDENTIALS_FILE=/var/www/teaching_panel/credentials.json

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/1

# Frontend
FRONTEND_URL=https://your-domain.com
```

---

## 🚀 АВТОМАТИЗАЦИЯ (опционально)

Если часто деплоишь, создай cron job для автоматического деплоя:

```bash
# Отредактируй crontab
sudo crontab -e

# Добавь строку (деплой каждый день в 2:00 AM UTC)
0 2 * * * cd /var/www/teaching_panel && sudo -u www-data git pull origin main && cd teaching_panel && source ../venv/bin/activate && pip install -r requirements.txt --quiet && python manage.py migrate --noinput && python manage.py collectstatic --noinput && sudo systemctl restart teaching_panel teaching_panel

# Или используй скрипт
0 2 * * * bash /var/www/teaching_panel/deploy_prod.sh >> /var/log/teaching_panel_deploy.log 2>&1
```

---

## 📈 МОНИТОРИНГ ПОСЛЕ ДЕПЛОЯ

Важные метрики для проверки:

```bash
# 1. Процессы Django (должны быть gunicorn или подобное)
ps aux | grep gunicorn

# 2. Открытые порты (8000 для Django, 80 для Nginx)
sudo netstat -tulpn | grep LISTEN

# 3. Использование памяти
free -h

# 4. Использование диска
df -h /var/www/

# 5. Количество ошибок в логах
sudo journalctl -u teaching_panel -p err -n 20
```

---

## ✅ ЧЕКЛИСТ ПЕРЕД И ПОСЛЕ ДЕПЛОЯ

### ДО ДЕПЛОЯ:
- [ ] Все изменения закоммичены в main
- [ ] Тесты прошли локально
- [ ] Нет merge conflicts
- [ ] Бэкап БД создан (если важно)
- [ ] SSH ключи настроены

### ПОСЛЕ ДЕПЛОЯ:
- [ ] Сервис teaching_panel running
- [ ] Nginx running
- [ ] API отвечает на запросы
- [ ] Логи не содержат ошибок
- [ ] Фронтенд загружается
- [ ] Основные функции работают
- [ ] Нет 500 ошибок

---

## 🎯 SUMMARY

**Самый быстрый способ:**

```bash
ssh tp << 'EOF'
cd /var/www/teaching_panel && \
sudo -u www-data git pull origin main && \
cd teaching_panel && \
source ../venv/bin/activate && \
pip install -r requirements.txt --quiet && \
python manage.py migrate && \
python manage.py collectstatic --noinput && \
sudo systemctl restart teaching_panel nginx && \
echo "✅ OK!"
EOF
```

**Готово! Teaching Panel теперь на production! 🚀**
