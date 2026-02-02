# План обновления Python 3.8 → 3.11 на Production

## Текущее состояние
- **OS**: Ubuntu 20.04.6 LTS (Focal Fossa)
- **Python**: 3.8.10 (system default)
- **venv**: `/var/www/teaching_panel/venv`

## Причины обновления
1. Python 3.8 EOL: октябрь 2024 (уже не поддерживается!)
2. Предупреждения от google.api_core о неподдерживаемой версии
3. Улучшения производительности в 3.10+
4. Новые фичи языка (match/case, better error messages)

## Шаги обновления

### 1. Установка Python 3.11 через deadsnakes PPA
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

### 2. Создание нового venv
```bash
cd /var/www/teaching_panel
sudo -u www-data python3.11 -m venv venv311
sudo -u www-data venv311/bin/pip install --upgrade pip wheel
sudo -u www-data venv311/bin/pip install -r requirements.txt
```

### 3. Тестирование
```bash
# Проверка что все зависимости установлены
venv311/bin/python -c "import django; print(django.VERSION)"
venv311/bin/python manage.py check

# Тест миграций
venv311/bin/python manage.py migrate --check
```

### 4. Переключение (в maintenance window!)
```bash
# Остановка сервисов
sudo systemctl stop teaching_panel celery celery-beat telegram_bot support_bot

# Бэкап старого venv
sudo mv venv venv38_backup

# Активация нового
sudo mv venv311 venv

# Перезапуск
sudo systemctl start teaching_panel celery celery-beat telegram_bot support_bot
```

### 5. Проверка после обновления
```bash
# Проверка версии
/var/www/teaching_panel/venv/bin/python --version  # Should be 3.11.x

# Smoke tests
curl -s https://lectio.tw1.ru/api/health/
sudo journalctl -u teaching_panel -n 20 --no-pager
```

### 6. Rollback (если что-то пошло не так)
```bash
sudo systemctl stop teaching_panel celery celery-beat
sudo mv venv venv311_broken
sudo mv venv38_backup venv
sudo systemctl start teaching_panel celery celery-beat
```

## Время на обновление
- ~30 минут с тестированием
- Требуется maintenance window (1-2 минуты downtime)

## Риски
- Несовместимость зависимостей (низкий риск для Django 5.x)
- Изменения в behavior (очень низкий риск)

## Рекомендация
Обновление можно провести в ближайшее maintenance window.
Python 3.8 уже не получает security updates!
