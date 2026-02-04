# 📦 Production Deploy Guide

## Процесс переноса изменений: Staging → Production

### 🎯 Перед началом

**Checklist:**
- [ ] Staging протестирован и работает корректно
- [ ] Все изменения закоммичены в git
- [ ] Нет критичных ошибок в логах staging
- [ ] Уведомлены пользователи (если ожидается downtime)

---

## 🚀 Автоматический деплой

```powershell
# Запуск скрипта автодеплоя (рекомендуется)
.\deploy_to_production.ps1
```

---

## 🛠️ Ручной деплой (пошагово)

### 1. Бэкап production БД

```bash
# На сервере
cd /var/www/teaching_panel
sudo -u www-data venv/bin/python manage.py dumpdata \
  --natural-foreign --natural-primary \
  --exclude contenttypes --exclude auth.Permission \
  > /tmp/backup_$(date +%Y%m%d_%H%M%S).json

# Также можно бэкапнуть SQLite файл
sudo cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)
```

### 2. Обновление кода

```bash
# Git pull
cd /var/www/teaching_panel
sudo git pull origin main

# Проверка изменений
git log -1 --oneline
git diff HEAD~1 HEAD --stat
```

### 3. Обновление зависимостей (если нужно)

```bash
# Проверка изменений в requirements.txt
git diff HEAD~1 HEAD teaching_panel/requirements.txt

# Если изменился - обновить пакеты
cd /var/www/teaching_panel
sudo -u www-data venv/bin/pip install -r teaching_panel/requirements.txt
```

### 4. Сборка frontend (если изменился)

```bash
# Проверка изменений frontend
git diff HEAD~1 HEAD --name-only | grep "^frontend/"

# Если изменился - пересборка
cd /var/www/teaching_panel/frontend
npm install  # Если package.json изменился
npm run build
```

### 5. Миграции БД

```bash
cd /var/www/teaching_panel

# Проверка новых миграций
sudo -u www-data venv/bin/python manage.py migrate --plan

# Применение миграций
sudo -u www-data venv/bin/python manage.py migrate
```

### 6. Статические файлы (если изменились)

```bash
cd /var/www/teaching_panel
sudo -u www-data venv/bin/python manage.py collectstatic --noinput
```

### 7. Перезапуск сервисов

```bash
# Перезапуск Gunicorn
sudo systemctl restart teaching-panel

# Проверка статуса
sudo systemctl status teaching-panel

# Если упал - смотрим логи
sudo journalctl -u teaching-panel -n 50 --no-pager
sudo tail -50 /var/log/teaching-panel-error.log
```

### 8. Smoke Tests

```bash
# Health check
curl -I https://lectiospace.ru/api/health/

# Тест авторизации
curl https://lectiospace.ru/api/jwt/token/ -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.ru","password":"test"}'

# Проверка главной страницы
curl -I https://lectiospace.ru/
```

---

## 🔄 Откат изменений (если что-то пошло не так)

### Откат кода

```bash
# Откат git на предыдущий коммит
cd /var/www/teaching_panel
sudo git reset --hard HEAD~1

# Перезапуск
sudo systemctl restart teaching-panel
```

### Откат БД

```bash
# Восстановление из дампа
cd /var/www/teaching_panel
sudo -u www-data venv/bin/python manage.py loaddata /tmp/backup_YYYYMMDD_HHMMSS.json

# Или восстановление SQLite файла
sudo cp db.sqlite3.backup_YYYYMMDD_HHMMSS db.sqlite3
sudo chown www-data:www-data db.sqlite3
sudo systemctl restart teaching-panel
```

---

## 📊 Мониторинг после деплоя

### Проверить логи (первые 15 минут)

```bash
# Логи приложения
sudo tail -f /var/log/teaching-panel-error.log

# Логи systemd
sudo journalctl -u teaching-panel -f

# Nginx логи
sudo tail -f /var/log/nginx/error.log
```

### Метрики для отслеживания

- Response time API endpoints (должен быть < 500ms)
- Error rate (должен быть 0% для критичных endpoints)
- Memory usage (не должен расти линейно)
- Active users (не должно быть резкого падения)

---

## 🎨 Best Practices

1. **Деплой в off-peak hours** (ночь или раннее утро)
2. **Gradual rollout**: сначала staging, потом production
3. **Feature flags**: для критичных изменений используй `settings.py` флаги
4. **Database migrations**: всегда backwards-compatible
5. **Monitoring**: следи за логами первые 30 минут после деплоя

---

## 🚨 Критичные изменения (требуют особой осторожности)

- **Миграции с data loss** (DROP TABLE, DROP COLUMN)
- **Изменение authentication/JWT** (может разлогинить всех)
- **Изменение payment flow** (критично для бизнеса)
- **Изменение Zoom integration** (может сломать уроки)

Для таких изменений:
1. Создай detailed rollback plan
2. Уведоми пользователей заранее
3. Делай в maintenance window
4. Имей человека on-call для быстрого отката

---

## 📝 Changelog

После деплоя обнови `CHANGELOG.md`:

```markdown
## [1.2.3] - 2026-02-04

### Added
- Новая фича X

### Changed
- Улучшена производительность Y

### Fixed
- Исправлена ошибка Z
```

---

## 🔗 Полезные команды

```bash
# Сравнение staging и production
diff <(ssh tp "cd /var/www/teaching-panel-stage && git log -1 --oneline") \
     <(ssh tp "cd /var/www/teaching_panel && git log -1 --oneline")

# Проверка версий пакетов
ssh tp "cd /var/www/teaching_panel && venv/bin/pip freeze | grep Django"
ssh tp "cd /var/www/teaching-panel-stage && venv/bin/pip freeze | grep Django"

# Сравнение конфигов
diff <(ssh tp "cat /etc/systemd/system/teaching-panel-stage.service") \
     <(ssh tp "cat /etc/systemd/system/teaching-panel.service")
```
