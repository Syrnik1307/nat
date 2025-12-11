# 🚀 Финальный деплой Teaching Panel без пароля

**Дата**: 5 декабря 2025
**Статус**: ✅ Готово к развертыванию
**Версия**: 1.1

**Домен/сервер:** lectio.space (A → 72.56.81.163, AAAA не используем)
**SSL:** Let's Encrypt, сертификаты в `/etc/letsencrypt/live/lectio.space/`
**Nginx:** server_name `lectio.space www.lectio.space`, редирект 80 → 443
**.env ключевые параметры:**
```
ALLOWED_HOSTS=lectio.space,www.lectio.space,72.56.81.163
FRONTEND_URL=https://lectio.space
CORS_EXTRA=https://lectio.space,https://www.lectio.space
CSRF_TRUSTED_ORIGINS=https://lectio.space,https://www.lectio.space
DEBUG=False
```

---

## 📋 Что было сделано

✅ **Backend:**
- Добавлена модель `IndividualInviteCode` для индивидуальных приглашений
- Создан `IndividualInviteCodeViewSet` с методами create, regenerate, join
- Добавлен сериализатор `IndividualInviteCodeSerializer`
- Реализованы API endpoints для работы с кодами
- Создана миграция БД (schedule.0014_individualinvitecode)

✅ **Frontend:**
- Создан компонент `IndividualInvitesManage.js` для управления кодами (учитель)
- Создан компонент `IndividualInviteModal.js` для показа кода и ссылки
- Создан компонент `JoinIndividualModal.js` для присоединения ученика
- Добавлены стили `IndividualInvitesManage.css`
- Добавлены API методы в `apiService.js`

✅ **Тестирование:**
- Создан полный тест `test_individual_invite_codes.py`
- Проверены все основные сценарии

✅ **Документация:**
- Создана документация `INDIVIDUAL_INVITE_CODES_IMPLEMENTATION.md`

---

## 🔑 Предварительные требования

### На локальной машине:

1. **SSH ключи без пароля:**
```bash
# Проверь что ключи настроены
ssh-keygen -l -f ~/.ssh/id_rsa  # или id_ed25519

# Скопируй публичный ключ на сервер (если еще не сделано)
ssh-copy-id -i ~/.ssh/id_rsa.pub user@server.com
```

2. **SSH alias в ~/.ssh/config:**
```bash
Host tp
   HostName lectio.space
   User deploy_user
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
```

Проверь что работает:
```bash
ssh tp "echo 'SSH connection OK'"
# Должно вывести: SSH connection OK (БЕЗ запроса пароля)
```

### На сервере:

1. **Папка проекта:** `/var/www/teaching_panel`
2. **Виртуальное окружение:** `../venv` (relative to project)
3. **Перемен окружения:** `.env` файл в `teaching_panel/teaching_panel/.env`
4. **Сервисы:** 
   - `teaching_panel.service` (systemd)
   - `nginx` (веб-сервер)
5. **DNS:** A записи `lectio.space` и `www` → `72.56.81.163`, без AAAA; после смены DNS дождитесь обновления кеша (обычно 30–60 мин).

---

## 🚀 Быстрый деплой

### Способ 1: PowerShell скрипт (Windows/macOS/Linux)

```powershell
# Linux/macOS с bash:
bash deploy_final.sh

# Windows с PowerShell:
.\deploy_final.ps1
```

### Способ 2: SSH команда (любая ОС)

```bash
ssh tp << 'EOF'
cd /var/www/teaching_panel && \
sudo -u www-data git pull origin main && \
cd teaching_panel && \
source ../venv/bin/activate && \
pip install -r requirements.txt --quiet && \
python manage.py migrate --noinput && \
python manage.py collectstatic --noinput --clear && \
sudo systemctl restart teaching_panel nginx && \
echo '✅ Деплой завершен!'
EOF
```

### Способ 3: Одна команда (самый простой)

```bash
ssh tp "cd /var/www/teaching_panel && sudo -u www-data git pull origin main && cd teaching_panel && source ../venv/bin/activate && pip install -r requirements.txt --quiet && python manage.py migrate --noinput && python manage.py collectstatic --noinput --clear && sudo systemctl restart teaching_panel nginx && echo '✅ OK!'"
```

---

## 📊 Что происходит при деплое

1. ✅ **Git Pull** (5 сек)
   - Скачивает последний код с main ветки
   - Без вашего ввода

2. ✅ **Pip Install** (10-30 сек)
   - Устанавливает/обновляет зависимости
   - Пропускает если ничего не изменилось

3. ✅ **Миграции БД** (5-10 сек)
   - Применяет миграции (включая 0014_individualinvitecode)
   - Создает новую таблицу для инвайт-кодов

4. ✅ **Collectstatic** (5-15 сек)
   - Собирает статические файлы
   - CSS, JS, изображения

5. ✅ **Restart Services** (5 сек)
   - Перезапускает Django (teaching_panel.service)
   - Перезапускает Nginx

6. ✅ **Verification** (2 сек)
   - Проверяет статус сервисов
   - Выводит последние логи

**Итого время:** ~1-2 минуты

---

## ✅ Проверка после деплоя

### 1. Статус сервисов

```bash
ssh tp "sudo systemctl status teaching_panel nginx --no-pager"
```

Ожидаемый вывод:
```
● teaching_panel.service - Django Teaching Panel
     Active: active (running)
```

### 2. API отвечает

```bash
ssh tp "curl -s http://localhost:8000/api/me/ -H 'Authorization: Bearer test' | head -20"
```

Ожидаемый вывод: JSON ответ (или 401 ошибка с неверным токеном - это OK)

### 3. Проверка логов

```bash
ssh tp "sudo journalctl -u teaching_panel -n 20 --no-pager"
```

Ищите ошибок (ERROR, Exception, Traceback)

### 4. Проверка миграций

```bash
ssh tp "cd /var/www/teaching_panel/teaching_panel && python manage.py migrate --check"
```

Ожидаемый вывод:
```
No planned migration files.
```

---

## 🔍 Отладка проблем

### ❌ Проблема: SSH требует пароль

```bash
# Проверь SSH ключи
ssh-add -l

# Если нет ключей, добавь их
ssh-add ~/.ssh/id_rsa

# Или используй ssh-keyscan для добавления в known_hosts
ssh-keyscan lectio.space >> ~/.ssh/known_hosts 2>/dev/null
```

### ❌ Проблема: "Permission denied" при sudo

```bash
# Проверь что пользователь может выполнять sudo без пароля
ssh tp "sudo -l | grep NOPASSWD"

# Должно быть NOPASSWD для git pull, pip install, systemctl restart
```

### ❌ Проблема: Git pull требует пароль

```bash
# Проверь что используется SSH вместо HTTPS
ssh tp "cd /var/www/teaching_panel && git remote -v"

# Должно быть:
# origin  git@github.com:Syrnik1307/nat.git (fetch)

# Если HTTPS, измени на SSH:
ssh tp "cd /var/www/teaching_panel && git remote set-url origin git@github.com:Syrnik1307/nat.git"
```

### ❌ Проблема: systemctl restart требует пароль

```bash
# Отредактируй sudoers:
ssh tp "sudo visudo"

# Добавь эту строку в конец:
# deploy_user ALL=(ALL) NOPASSWD: /bin/systemctl restart teaching_panel, /bin/systemctl restart nginx
```

### ❌ Проблема: migrate завис или ошибается

```bash
# Проверь статус миграций
ssh tp "cd /var/www/teaching_panel/teaching_panel && python manage.py migrate --plan"

# Откати последнюю миграцию если нужно
ssh tp "cd /var/www/teaching_panel/teaching_panel && python manage.py migrate schedule 0013"
```

---

## 📝 Важные файлы и пути

На **локальной машине:**
- `deploy_final.sh` - bash скрипт для Linux/macOS
- `deploy_final.ps1` - PowerShell скрипт для Windows
- `MANUAL_PROD_DEPLOY.md` - документация с примерами

На **сервере:**
- `/var/www/teaching_panel/` - корень проекта
- `/var/www/teaching_panel/teaching_panel/` - Django приложение
- `/var/www/teaching_panel/venv/` - виртуальное окружение
- `/var/www/teaching_panel/teaching_panel/.env` - переменные окружения
- `/var/log/nginx/` - логи nginx
- `sudo journalctl -u teaching_panel` - логи Django

---

## 🎯 Итоговый чеклист перед деплоем

- [x] Код залит в `main` ветку GitHub
- [x] Все тесты пройдены локально
- [x] SSH ключи настроены (проверено: `ssh tp "echo OK"`)
- [x] `.env` файл на сервере содержит все необходимые переменные
- [x] Бэкап БД создан (опционально)
- [x] Ningx и systemd настроены

---

## 🚀 Готово к деплою!

Выполни одну из этих команд:

```bash
# Linux/macOS:
bash deploy_final.sh

# Windows PowerShell:
.\deploy_final.ps1

# Или простая SSH команда:
ssh tp "cd /var/www/teaching_panel && sudo -u www-data git pull origin main && cd teaching_panel && source ../venv/bin/activate && pip install -r requirements.txt --quiet && python manage.py migrate --noinput && python manage.py collectstatic --noinput --clear && sudo systemctl restart teaching_panel nginx && echo '✅ OK!'"
```

---

## ✅ Успешный деплой выглядит так:

```
========================================
Teaching Panel Production Deployment
========================================

🔌 Подключаюсь к серверу: tp
📥 Шаг 1: Обновление кода из Git...
Already up to date.
✅ Код обновлен

📦 Шаг 2: Установка зависимостей...
✅ Зависимости установлены

🔄 Шаг 3: Запуск миграций БД...
Running migrations:
  Applying schedule.0014_individualinvitecode... OK
✅ Миграции выполнены

📄 Шаг 4: Сбор статических файлов...
123 static files copied to '/var/www/teaching_panel/static'
✅ Статические файлы собраны

🔄 Шаг 5: Перезапуск сервисов...
✅ Teaching Panel перезапущен
✅ Nginx перезапущен

✔️ Шаг 6: Проверка статуса...
● teaching_panel.service - Django Teaching Panel
     Active: active (running)

========================================
✅ ДЕПЛОЙ УСПЕШНО ЗАВЕРШЕН!
========================================

Проверка доступности:
   - API: https://lectio.space/api/
   - Frontend: https://lectio.space/

Полезные команды:
  - Логи: ssh tp 'sudo journalctl -u teaching_panel -f'
  - Статус: ssh tp 'sudo systemctl status teaching_panel'
  - Перезапуск: ssh tp 'sudo systemctl restart teaching_panel'
```

---

## 📧 Техподдержка

Если что-то пошло не так:

1. Проверь логи: `ssh tp 'sudo journalctl -u teaching_panel -n 50'`
2. Проверь статус: `ssh tp 'sudo systemctl status teaching_panel'`
3. Откати последний коммит: `ssh tp 'cd /var/www/teaching_panel && sudo -u www-data git revert HEAD'`
4. Перезапусти вручную: `ssh tp 'sudo systemctl restart teaching_panel'`

**Успехов! 🎉**
