# 🐘 Миграция Teaching Panel на PostgreSQL

## Выполни эти команды по порядку через SSH

### Шаг 1: Подключись к серверу
```bash
ssh tp
```

### Шаг 2: Установи PostgreSQL и Redis
```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib redis-server python3-dev libpq-dev
sudo systemctl enable postgresql redis-server
sudo systemctl start postgresql redis-server
```

### Шаг 3: Создай базу данных
```bash
# Генерируем пароль
DB_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)
echo "Сохрани пароль: $DB_PASSWORD"

# Создаём пользователя и БД
sudo -u postgres psql -c "CREATE USER teaching_panel WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE teaching_panel OWNER teaching_panel;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE teaching_panel TO teaching_panel;"
```

### Шаг 4: Сделай бэкап SQLite
```bash
cd /var/www/teaching_panel/teaching_panel

# Бэкап файла SQLite
sudo cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)

# Экспорт данных в JSON
source ../venv/bin/activate
python manage.py dumpdata --natural-foreign --natural-primary -o /var/www/teaching_panel/backup_before_postgres.json
```

### Шаг 5: Установи Python зависимости
```bash
source /var/www/teaching_panel/venv/bin/activate
pip install psycopg2-binary redis django-redis
```

### Шаг 6: Обнови .env файл
```bash
# Добавляем переменные (замени PASSWORD на реальный пароль из шага 3)
sudo tee -a /var/www/teaching_panel/.env << 'EOF'

# PostgreSQL
DATABASE_URL=postgres://teaching_panel:PASSWORD@localhost:5432/teaching_panel

# Redis
REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
EOF

# Отредактируй файл и замени PASSWORD на реальный пароль
sudo nano /var/www/teaching_panel/.env
```

### Шаг 7: Примени миграции в PostgreSQL
```bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

# Применяем миграции
python manage.py migrate

# Проверяем что БД работает
python manage.py shell -c "from django.contrib.auth import get_user_model; print('Tables OK:', get_user_model().objects.count())"
```

### Шаг 8: Загрузи данные в PostgreSQL
```bash
python manage.py loaddata /var/www/teaching_panel/backup_before_postgres.json
```

### Шаг 9: Перезапусти сервисы
```bash
sudo systemctl restart teaching_panel
sudo systemctl status teaching_panel
```

### Шаг 10: Проверь что всё работает
```bash
curl -s http://127.0.0.1:8000/api/ | head -20
```

---

## 🔧 Если что-то пошло не так

### Откат на SQLite:
```bash
# Удаляем DATABASE_URL из .env
sudo nano /var/www/teaching_panel/.env
# (удали строку DATABASE_URL=...)

# Восстанавливаем бэкап SQLite
cd /var/www/teaching_panel/teaching_panel
sudo cp db.sqlite3.backup_* db.sqlite3

# Перезапускаем
sudo systemctl restart teaching_panel
```

### Проверка логов:
```bash
sudo journalctl -u teaching_panel -f
```

---

## ✅ После успешной миграции

1. Проверь сайт в браузере
2. Залогинься как учитель и студент
3. Проверь расписание, группы, уроки
4. Удали старый SQLite файл:
   ```bash
   rm /var/www/teaching_panel/teaching_panel/db.sqlite3
   ```
