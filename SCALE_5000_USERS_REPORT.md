# 🚀 Отчёт: Масштабирование Teaching Panel LMS до 5000+ пользователей

**Дата:** 27 декабря 2025  
**Версия:** 1.0

---

## 📊 Текущее состояние Production

### Инфраструктура
| Параметр | Текущее значение | Требуемое для 5000 users |
|----------|-----------------|-------------------------|
| **CPU** | 1 ядро | 4-8 ядер |
| **RAM** | 1.9 GB | 8-16 GB |
| **База данных** | SQLite | PostgreSQL |
| **Кэш** | LocMem (in-process) | Redis |
| **Workers** | 5 Gunicorn | 8-12 Gunicorn + async |
| **Task Queue** | Не настроен | Celery + Redis |

### Данные
- **Пользователей:** 26 (2 учителя, 21 студент)
- **Групп:** 3
- **Уроков:** 12
- **Zoom аккаунтов:** 3

---

## 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### 1. SQLite не выдержит нагрузку
**Проблема:** SQLite блокирует всю БД при любой записи. При 5000 пользователях будут постоянные конфликты.

**Решение:**
```bash
# На сервере
sudo apt install postgresql postgresql-contrib
sudo -u postgres createuser --interactive teaching_panel
sudo -u postgres createdb teaching_panel -O teaching_panel

# В .env добавить:
DATABASE_URL=postgres://teaching_panel:password@localhost:5432/teaching_panel
```

### 2. Отсутствие Redis для кэша
**Проблема:** LocMem кэш не разделяется между Gunicorn workers. Каждый worker имеет свой кэш → неэффективно.

**Решение:**
```bash
# Установка Redis
sudo apt install redis-server
sudo systemctl enable redis-server

# В .env добавить:
REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
```

### 3. Недостаточно ресурсов сервера
**Проблема:** 1 CPU + 1.9 GB RAM не выдержит concurrent load.

**Решение:**
Минимальные требования для 5000 users:
- **CPU:** 4 cores (рекомендуется 8)
- **RAM:** 8 GB (рекомендуется 16 GB)
- **SSD:** 50+ GB
- **Сеть:** 100+ Mbps

### 4. Zoom Pool слишком мал
**Проблема:** Только 3 Zoom аккаунта. При одновременных уроках будет недостаток.

**Формула:** 
```
Нужных аккаунтов = (Кол-во учителей × Пик одновременных уроков) / Среднее время урока
```

Для 100 учителей с пиком 30% одновременных уроков: **~30 Zoom аккаунтов**

---

## 🟡 ВАЖНЫЕ УЛУЧШЕНИЯ

### 5. Оптимизация Gunicorn
Текущая конфигурация хорошая, но нужно увеличить workers:

```ini
# /etc/systemd/system/teaching_panel.service
ExecStart=/var/www/teaching_panel/venv/bin/gunicorn teaching_panel.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 9 \                 # (2 × CPU + 1) для 4 cores
  --threads 4 \                 # Добавить threads для I/O bound
  --worker-class gthread \      # Threaded workers
  --timeout 120 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --keep-alive 5 \
  --log-level warning
```

### 6. Включить Connection Pooling для БД
```python
# settings.py - уже настроено, но нужен PostgreSQL
DATABASES = {
    'default': dj_database_url.config(
        conn_max_age=600,        # ✅ Уже есть
        conn_health_checks=True, # ✅ Уже есть
    )
}
```

### 7. Добавить индексы в БД (если отсутствуют)
```sql
-- Проверить после миграции на PostgreSQL
CREATE INDEX CONCURRENTLY idx_lessons_start_time ON schedule_lesson(start_time);
CREATE INDEX CONCURRENTLY idx_lessons_teacher ON schedule_lesson(teacher_id, start_time);
CREATE INDEX CONCURRENTLY idx_groups_teacher ON schedule_group(teacher_id);
```

---

## 🟢 УЖЕ РЕАЛИЗОВАНО (ХОРОШО!)

### ✅ N+1 Query Prevention
Код использует `select_related()` и `prefetch_related()`:
- `GroupViewSet.get_queryset()` - select_related('teacher').prefetch_related('students')
- `LessonViewSet.get_queryset()` - select_related('group', 'teacher', 'zoom_account')
- Recordings, Attendance, etc. - все оптимизированы

### ✅ Rate Limiting
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'user': '3000/hour',      # ✅ Подходит для 5000 users
        'anon': '200/hour',
        'login': '50/hour',
        'submissions': '100/hour',
        'grading': '500/hour',
    }
}
```

### ✅ Индексы в моделях
- `Lesson.start_time` - db_index
- `ZoomAccount.is_busy` - db_index
- Composite indexes на (teacher, start_time), (group, start_time)

### ✅ Кэширование критических данных
- Calendar feed кэшируется 60 секунд
- Zoom tokens кэшируются 3000 секунд
- Rate limiting использует кэш

### ✅ JWT Authentication
- Access token: 30 минут
- Refresh token: 7 дней
- Token blacklist включён

---

## 📋 ПЛАН МИГРАЦИИ

### Фаза 1: Инфраструктура (1-2 дня)
```bash
# 1. Upgrade сервера до 4 CPU / 8 GB RAM

# 2. Установка PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib python3-dev libpq-dev

# 3. Создание БД
sudo -u postgres psql
CREATE USER teaching_panel WITH PASSWORD 'secure_password_here';
CREATE DATABASE teaching_panel OWNER teaching_panel;
\q

# 4. Установка Redis
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 5. Pip dependencies
pip install psycopg2-binary redis django-redis
```

### Фаза 2: Миграция данных (2-3 часа)
```bash
# 1. Backup SQLite
cp db.sqlite3 db.sqlite3.backup

# 2. Export данных
python manage.py dumpdata --natural-foreign --natural-primary -o backup.json

# 3. Обновить .env
echo 'DATABASE_URL=postgres://teaching_panel:password@localhost:5432/teaching_panel' >> .env
echo 'REDIS_URL=redis://127.0.0.1:6379/1' >> .env
echo 'CELERY_BROKER_URL=redis://127.0.0.1:6379/0' >> .env

# 4. Применить миграции
python manage.py migrate

# 5. Загрузить данные
python manage.py loaddata backup.json
```

### Фаза 3: Оптимизация (1 день)
```bash
# 1. Обновить Gunicorn конфиг
sudo systemctl edit teaching_panel
# Добавить --workers 9 --threads 4 --worker-class gthread

# 2. Настроить Celery
sudo nano /etc/systemd/system/celery.service
sudo systemctl enable celery
sudo systemctl start celery

# 3. Перезапуск сервисов
sudo systemctl daemon-reload
sudo systemctl restart teaching_panel nginx
```

### Фаза 4: Тестирование (1 день)
```bash
# Установить Locust локально
pip install locust

# Создать 5000 тестовых пользователей
python manage.py shell < create_load_test_users.py

# Запустить нагрузочное тестирование
locust -f locustfile.py --host=https://lectio.space --headless \
  --users 5000 --spawn-rate 100 --run-time 10m \
  --html=load_test_5000_users.html
```

---

## 📊 Целевые метрики для 5000 пользователей

| Метрика | Целевое значение | Критическое |
|---------|-----------------|-------------|
| **Response Time P50** | < 100ms | > 500ms |
| **Response Time P95** | < 300ms | > 1000ms |
| **Response Time P99** | < 500ms | > 2000ms |
| **Requests/sec** | > 500 RPS | < 100 RPS |
| **Error Rate** | < 0.1% | > 1% |
| **CPU Usage** | < 70% | > 90% |
| **Memory Usage** | < 80% | > 95% |
| **DB Connections** | < 80% pool | > 95% pool |

---

## 💰 Оценка стоимости

### Вариант 1: VPS (DigitalOcean/Linode)
| Ресурс | Specs | Цена/мес |
|--------|-------|----------|
| Web Server | 4 CPU / 8 GB RAM | $48 |
| Database | Managed PostgreSQL | $15 |
| Redis | Managed Redis | $15 |
| **Итого** | | **~$80/мес** |

### Вариант 2: Один мощный сервер
| Ресурс | Specs | Цена/мес |
|--------|-------|----------|
| Dedicated | 8 CPU / 16 GB RAM | $80 |
| PostgreSQL + Redis | На том же сервере | $0 |
| **Итого** | | **~$80/мес** |

### Вариант 3: Cloud (Azure/AWS) с автоскейлингом
| Ресурс | Specs | Цена/мес |
|--------|-------|----------|
| App Service | B2 + autoscale | $50-150 |
| Azure Cosmos DB | Serverless | $0-50 |
| Redis Cache | Basic | $20 |
| **Итого** | | **$70-220/мес** |

---

## 🔒 Security Checklist

- [ ] Заменить reCAPTCHA test keys на production
- [ ] Включить HTTPS redirect: `SECURE_SSL_REDIRECT=True`
- [ ] Включить secure cookies: `SESSION_COOKIE_SECURE=True`
- [ ] Настроить HSTS: `SECURE_HSTS_SECONDS=31536000`
- [ ] Обновить SECRET_KEY на уникальный
- [ ] Настроить Sentry для мониторинга
- [ ] Регулярные бэкапы PostgreSQL

---

## 📝 Скрипт для создания тестовых пользователей

Создайте файл `create_5000_test_users.py`:

```python
"""
Создание 5000 тестовых пользователей для нагрузочного тестирования
Запуск: python manage.py shell < create_5000_test_users.py
"""
from django.contrib.auth import get_user_model
from schedule.models import Group
import random

User = get_user_model()

# Создаём 500 учителей
print("Creating 500 teachers...")
teachers = []
for i in range(1, 501):
    email = f"teacher{i}@loadtest.local"
    if not User.objects.filter(email=email).exists():
        u = User.objects.create_user(
            email=email,
            password="loadtest123",
            role="teacher",
            first_name=f"Teacher{i}",
            last_name="LoadTest"
        )
        teachers.append(u)
    if i % 100 == 0:
        print(f"  Created {i} teachers...")

# Создаём 4500 студентов
print("Creating 4500 students...")
for i in range(1, 4501):
    email = f"student{i}@loadtest.local"
    if not User.objects.filter(email=email).exists():
        User.objects.create_user(
            email=email,
            password="loadtest123",
            role="student",
            first_name=f"Student{i}",
            last_name="LoadTest"
        )
    if i % 500 == 0:
        print(f"  Created {i} students...")

# Создаём группы для каждого учителя
print("Creating groups...")
teachers = User.objects.filter(role="teacher", email__endswith="@loadtest.local")
students = list(User.objects.filter(role="student", email__endswith="@loadtest.local"))

for teacher in teachers[:100]:  # Первые 100 учителей с группами
    group_name = f"Group_{teacher.email.split('@')[0]}"
    if not Group.objects.filter(name=group_name).exists():
        group = Group.objects.create(
            name=group_name,
            teacher=teacher,
            description="Load test group"
        )
        # Добавляем 30-50 студентов в каждую группу
        sample_students = random.sample(students, min(40, len(students)))
        group.students.set(sample_students)

print("Done!")
print(f"Total users: {User.objects.count()}")
print(f"Teachers: {User.objects.filter(role='teacher').count()}")
print(f"Students: {User.objects.filter(role='student').count()}")
print(f"Groups: {Group.objects.count()}")
```

---

## ✅ Итоговые рекомендации

### Немедленно (Блокеры):
1. **Upgrade сервера** до минимум 4 CPU / 8 GB RAM
2. **Мигрировать на PostgreSQL** - SQLite не подходит для production
3. **Установить Redis** для кэша и Celery

### В ближайшее время:
4. Добавить больше **Zoom аккаунтов** в пул (минимум 20-30)
5. Настроить **Celery** для фоновых задач
6. Заменить **reCAPTCHA test keys**

### Перед launch:
7. Провести **нагрузочное тестирование** с Locust
8. Настроить **мониторинг** (Sentry уже подготовлен)
9. Настроить **автоматические бэкапы**

---

**Вывод:** Код проекта хорошо оптимизирован (N+1 prevention, индексы, кэширование). Основные проблемы - инфраструктурные: SQLite, отсутствие Redis, недостаточные ресурсы сервера. После миграции на PostgreSQL + Redis и upgrade сервера, система готова к 5000+ пользователей.

---

*Отчёт сгенерирован автоматически на основе анализа кодовой базы и production окружения.*
