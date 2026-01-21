# Docker Quickstart (Teaching Panel)

Этот набор файлов **не меняет код приложения** — только добавляет инфраструктуру для запуска через Docker.

---

## Структура файлов

```
docker-compose.yml           # Локальная разработка (SQLite, Redis)
docker-compose.prod.yml      # Production (PostgreSQL, SSL-ready, масштабируемый)
.env.production.example      # Шаблон переменных для прода

docker/
├── backend/
│   ├── Dockerfile           # Dev образ
│   ├── Dockerfile.prod      # Production образ (non-root user, healthcheck)
│   ├── entrypoint.sh        # Dev entrypoint
│   └── entrypoint.prod.sh   # Prod entrypoint (ждёт Postgres, настраивает workers)
└── nginx/
    ├── Dockerfile           # Dev nginx
    ├── Dockerfile.prod      # Prod nginx (с SSL, rate limiting)
    ├── nginx.conf           # Dev конфиг
    ├── nginx.prod.conf      # Prod конфиг
    └── locations.conf       # Общие locations (API proxy, caching)
```

---

## Локальная разработка (Windows/Mac/Linux)

1) Установите Docker Desktop
2) Запустите:
```bash
docker compose up --build
```
3) Откройте `http://localhost:8080`

Остановить: `docker compose down`
Снести всё с данными: `docker compose down -v`

---

## Production Deploy (1000+ учителей, 10000+ учеников)

### 1. Подготовка сервера

```bash
# Установите Docker + compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Склонируйте репозиторий
git clone <your-repo> /var/www/teaching_panel
cd /var/www/teaching_panel
```

### 2. Настройка окружения

```bash
# Скопируйте шаблон
cp .env.production.example .env.production

# Заполните ОБЯЗАТЕЛЬНЫЕ переменные:
nano .env.production
```

**Минимум для старта:**
- `SECRET_KEY` — сгенерировать: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `POSTGRES_PASSWORD` — надёжный пароль
- `ALLOWED_HOSTS` — ваш домен

### 3. SSL сертификаты (Let's Encrypt)

```bash
mkdir -p docker/nginx/ssl

# Получить через certbot
sudo certbot certonly --standalone -d yourdomain.com

# Скопировать в Docker
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/nginx/ssl/
sudo chmod 644 docker/nginx/ssl/*.pem
```

Затем раскомментируйте HTTPS блок в `docker/nginx/nginx.prod.conf`.

### 4. Запуск

```bash
# Первый запуск (сборка + миграции)
docker compose -f docker-compose.prod.yml up --build -d

# Проверка статуса
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend

# Создать админа
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### 5. Масштабирование Celery (при высокой нагрузке)

```bash
# Добавить 4 воркера
docker compose -f docker-compose.prod.yml up -d --scale celery=4

# Проверить
docker compose -f docker-compose.prod.yml ps
```

---

## Полезные команды

```bash
# Логи
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f celery
docker compose -f docker-compose.prod.yml logs -f nginx

# Django shell
docker compose -f docker-compose.prod.yml exec backend python manage.py shell

# Миграции вручную
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Перезапуск без пересборки
docker compose -f docker-compose.prod.yml restart backend

# Полная пересборка
docker compose -f docker-compose.prod.yml up --build -d

# Остановка
docker compose -f docker-compose.prod.yml down

# Удаление с данными (ОСТОРОЖНО!)
docker compose -f docker-compose.prod.yml down -v
```

---

## Мониторинг и Health Checks

- `/api/health/` — глубокий healthcheck (проверяет DB)
- `/health` — быстрый healthcheck для nginx/load balancer
- Все контейнеры имеют встроенные healthchecks

Проверить здоровье:
```bash
docker compose -f docker-compose.prod.yml ps
curl http://localhost/api/health/
```

---

## Ресурсы и лимиты (настроены в docker-compose.prod.yml)

| Сервис | RAM Limit | Рекомендуемый сервер |
|--------|-----------|---------------------|
| backend | 1 GB | |
| celery (×1) | 1 GB | |
| celery_beat | 256 MB | |
| redis | 600 MB | |
| postgres | 1 GB | |
| nginx | 256 MB | |

**Минимум для 10000 пользователей:** 4 GB RAM, 2 vCPU
**Рекомендуется:** 8 GB RAM, 4 vCPU + 2-4 celery workers

---

## Обновление (zero-downtime)

```bash
cd /var/www/teaching_panel
git pull origin main

# Пересобрать только изменившиеся образы
docker compose -f docker-compose.prod.yml build

# Rolling restart (nginx остаётся онлайн)
docker compose -f docker-compose.prod.yml up -d --no-deps backend
docker compose -f docker-compose.prod.yml up -d --no-deps celery
docker compose -f docker-compose.prod.yml up -d --no-deps nginx
```

---

## Backup PostgreSQL

```bash
# Создать бэкап
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U teaching_panel teaching_panel > backup_$(date +%Y%m%d).sql

# Восстановить
cat backup_20260122.sql | docker compose -f docker-compose.prod.yml exec -T postgres psql -U teaching_panel teaching_panel
```
