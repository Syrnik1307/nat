# 🚀 ДЕПЛОЙ TP НА PRODUCTION - ПОЛНАЯ ИНСТРУКЦИЯ

**Дата**: 5 декабря 2025  
**Для**: Teaching Panel (Django + React + Zoom + YooKassa + Google Drive)  
**БЕЗ ПАРОЛЯ**: Используется SSH ключи (no password)

---

## ⚡ САМЫЙ БЫСТРЫЙ СПОСОБ (30 секунд)

### Вариант 1: Из PowerShell (Windows)

Открой PowerShell и выполни:

```powershell
cd c:\Users\User\Desktop\nat
.\deploy_to_prod.ps1
```

**Что это делает:**
- Подключается к серверу по SSH (без пароля)
- Тянет код из main ветки
- Устанавливает зависимости Python
- Запускает миграции БД
- Собирает статические файлы
- Перезапускает все сервисы
- Показывает статус

---

### Вариант 2: Из Bash/Терминала (Mac/Linux/WSL)

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
echo "✅ DEPLOYMENT COMPLETE!" && \
sudo systemctl status teaching_panel --no-pager | head -10
EOF
```

---

## 📋 ПОШАГОВЫЙ ДЕПЛОЙ (если что-то пошло не так)

### ШАГ 1: Подготовка SSH (ОДИН РАЗ)

Чтобы деплоить без пароля, нужны SSH ключи. Проверь что они есть:

```bash
# Проверь есть ли SSH ключ
ls ~/.ssh/id_rsa
ls ~/.ssh/id_ed25519

# Если нет, создай
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

# Загрузи публичный ключ на сервер (один раз)
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@your-server-ip
```

Или добавь в `~/.ssh/config`:

```
Host tp
    HostName your-server-ip
    User www-data
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
```

**После этого работает:** `ssh tp` без пароля ✅

---

### ШАГ 2: Подключение к серверу

```bash
# Если есть alias
ssh tp

# Или напрямую
ssh user@123.45.67.89
```

---

### ШАГ 3: Обновление кода

Перейди в папку проекта на сервере:

```bash
cd /var/www/teaching_panel
```

Скачай новый код из Git:

```bash
sudo -u www-data git pull origin main
```

**Ожидаемый результат:**
```
remote: Counting objects: 25, done.
From https://github.com/Syrnik1307/nat
   abc1234..def5678  main       -> origin/main
Updating abc1234..def5678
Fast-forward
 teaching_panel/settings.py     |  5 ++---
 frontend/src/components/NavBar.js | 10 +++----
 2 files changed, 7 insertions(+), 8 deletions(-)
```

---

### ШАГ 4: Установка Python зависимостей

```bash
# Перейди в папку Django
cd teaching_panel

# Активируй виртуальное окружение
source ../venv/bin/activate

# Установи зависимости
pip install -r requirements.txt
```

**Ожидаемый результат:**
```
Collecting django==5.2.0
  Using cached django-5.2.0-py3-none-any.whl (8.1 MB)
...
Successfully installed django-5.2.0 djangorestframework-3.14.0 ...
```

---

### ШАГ 5: Миграции БД

```bash
python manage.py migrate
```

**Ожидаемый результат:**
```
Operations to perform:
  Apply all migrations: accounts, core, schedule, zoom_pool, homework, analytics, ...
Running migrations:
  Applying accounts.0001_initial... OK
  Applying accounts.0002_user_telegram_username... OK
  Applying core.0001_initial... OK
  ...
  All migrations applied successfully!
```

**Если выдает ошибку "No changes detected"** - это нормально, значит все уже применено.

---

### ШАГ 6: Сбор статических файлов

```bash
python manage.py collectstatic --noinput
```

**Ожидаемый результат:**
```
You have requested to collect static files at the destination
location as specified in your settings.

123 static files copied to '/var/www/teaching_panel/static'
0 unmodified.
0 post-processed.
```

---

### ШАГ 7: Перезапуск сервисов

```bash
# Основной Django сервис
sudo systemctl restart teaching_panel

# Веб-сервер
sudo systemctl restart nginx

# (опционально) Очереди задач
sudo systemctl restart redis-server
sudo systemctl restart celery
sudo systemctl restart celery-beat
```

---

### ШАГ 8: Проверка статуса

```bash
# Статус Django
sudo systemctl status teaching_panel --no-pager

# Статус Nginx
sudo systemctl status nginx --no-pager

# Последние логи (ищи ошибки)
sudo journalctl -u teaching_panel -n 30
```

**ДОЛЖНО БЫТЬ:**
```
● teaching_panel.service - Django Teaching Panel
     Loaded: loaded (/etc/systemd/system/teaching_panel.service; enabled)
     Active: active (running) since ... ago
     Main PID: 12345 (gunicorn)
```

---

### ШАГ 9: Финальная проверка

```bash
# API должно отвечать
curl http://localhost:8000/api/me/

# Или если через Nginx
curl http://your-domain.com/api/me/

# Проверка синхронизации БД
python manage.py migrate --check
```

---

## 🔧 РАСШИРЕННЫЕ КОМАНДЫ

### Если нужна именно сборка Frontend

```bash
cd /var/www/teaching_panel/frontend
npm install
npm run build
```

### Если нужна полная переустановка зависимостей

```bash
cd /var/www/teaching_panel/teaching_panel
rm -rf ../venv
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
```

### Если нужна переустановка npm модулей

```bash
cd /var/www/teaching_panel/frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Если нужно очистить весь кэш

```bash
cd /var/www/teaching_panel/teaching_panel
python manage.py clear_cache
python manage.py migrate --flush  # ВНИМАНИЕ: удалит все данные!
```

---

## 🐛 ЧАСТЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ

### ❌ `git pull` требует пароль

**Проблема:** Git настроен на HTTPS вместо SSH

**Решение:**
```bash
# Проверь текущий URL
git remote -v

# Если видишь https://, измени на SSH
git remote set-url origin git@github.com:Syrnik1307/nat.git

# Проверь что изменилось
git remote -v
```

---

### ❌ `pip install` очень медленный

**Решение:** Используй `--quiet` флаг чтобы скрыть вывод

```bash
pip install -r requirements.txt --quiet
```

Или просто уходи пить кофе, обычно это 2-5 минут.

---

### ❌ `Permission denied` при collectstatic

**Проблема:** www-data не может писать в папку static

**Решение:**
```bash
# Измени владельца папки
sudo chown -R www-data:www-data /var/www/teaching_panel

# Или дай права
sudo chmod -R 755 /var/www/teaching_panel
```

---

### ❌ Teaching Panel не запускается

**Проверь логи:**
```bash
sudo journalctl -u teaching_panel -n 50
```

**Частые причины:**
1. **ImportError** - неустановленный модуль → `pip install -r requirements.txt`
2. **psycopg2 error** - проблема с БД → проверь DATABASE_URL в .env
3. **ModuleNotFoundError** - старые bytecode файлы → `find . -type d -name __pycache__ -exec rm -r {} +`
4. **Permission denied** - проблема с правами → `sudo chown -R www-data:www-data /var/www/teaching_panel`

---

### ❌ Nginx показывает 502 Bad Gateway

**Это значит:**
- Django не запущен → проверь `systemctl status teaching_panel`
- Неправильный unix socket → проверь `/etc/systemd/system/teaching_panel.service`
- Неправильный путь в nginx config → проверь `/etc/nginx/sites-available/teaching_panel`

**Решение:**
```bash
# Перезапусти всё
sudo systemctl restart teaching_panel
sudo systemctl restart nginx

# Проверь логи
sudo tail -f /var/log/nginx/error.log
```

---

## 📊 ПОСЛЕ УСПЕШНОГО ДЕПЛОЯ

### Команды для проверки

```bash
# 1. Процессы запущены?
ps aux | grep gunicorn
ps aux | grep nginx

# 2. Порты слушают?
sudo netstat -tulpn | grep LISTEN | grep -E ":(80|8000|443)"

# 3. Памяти хватает?
free -h

# 4. Диск не заполнен?
df -h /var/www/

# 5. Ошибок в логах?
sudo journalctl -u teaching_panel -p err -n 20

# 6. API отвечает?
curl -s http://localhost:8000/api/me/ | head -c 100
```

---

## ✅ ЧЕКЛИСТ

### ДО ДЕПЛОЯ:
- [ ] Коммиты запушены в main
- [ ] Код не сломан (тесты прошли)
- [ ] .env файл на сервере настроен
- [ ] Бэкап БД создан (если критично)
- [ ] SSH ключи настроены (no password auth)

### ПОСЛЕ ДЕПЛОЯ:
- [ ] `systemctl status teaching_panel` = **active (running)**
- [ ] `systemctl status nginx` = **active (running)**
- [ ] `curl http://localhost:8000/api/me/` отвечает
- [ ] Логи без **ERROR** или **CRITICAL**
- [ ] Фронтенд загружается в браузере
- [ ] Основные функции работают
- [ ] Нет 500 ошибок

---

## 🎯 ONE-LINER (скопируй целиком)

```bash
ssh tp "cd /var/www/teaching_panel && sudo -u www-data git pull origin main && cd teaching_panel && source ../venv/bin/activate && pip install -r requirements.txt --quiet && python manage.py migrate && python manage.py collectstatic --noinput && sudo systemctl restart teaching_panel nginx && echo '✅ DONE!' && sudo systemctl status teaching_panel --no-pager | head -5"
```

---

## 📚 ДОКУМЕНТАЦИЯ

- **Для мониторинга**: `PRODUCTION_OPERATIONS_AND_CHAT_GUIDE.md`
- **Для настройки сервера**: `PRE_DEPLOYMENT_CHECKLIST.md`
- **Для логирования**: `MANUAL_DEPLOY_GUIDE.md`
- **Для Zoom**: `CORE_MODULE_COMPLETED.md`
- **Для YooKassa**: `BACKEND_SUBSCRIPTIONS_GUIDE.md`

---

## 🚀 ТЫ ГОТОВ!

**Teaching Panel готов к production deployment!**

Выполни команду и система будет live за 2 минуты:

```bash
ssh tp << 'EOF'
cd /var/www/teaching_panel && sudo -u www-data git pull origin main && cd teaching_panel && source ../venv/bin/activate && pip install -r requirements.txt --quiet && python manage.py migrate && python manage.py collectstatic --noinput && sudo systemctl restart teaching_panel nginx && echo "✅ TP IS LIVE!"
EOF
```

**Good luck! 🎉**
