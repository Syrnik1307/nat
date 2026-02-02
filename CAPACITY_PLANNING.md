# 📊 Lectio Space: Infrastructure Capacity Planning

## Обзор

Этот документ описывает требования к инфраструктуре для Lectio Space LMS на разных этапах роста.

## Текущие узкие места (выявлены)

1. **PostgreSQL Connections** — `OperationalError` при нехватке соединений
2. **Memory pressure** — OOM kills на 2GB сервере при video processing
3. **CPU spikes** — FFmpeg сжатие блокирует web запросы

## Решения применены в конфигах

| Проблема | Решение | Stage |
|----------|---------|-------|
| DB connections | PgBouncer (transaction pooling) | B+ |
| Memory leaks | `max-requests`, `max-memory-per-child` | Все |
| FFmpeg blocking | Отдельный heavy queue | B+ |
| Slow queries | `statement_timeout=30s` | Все |

---

## Stage A: MVP (текущий)

**Целевая аудитория:** 300 учителей / 3,000 учеников

### Характеристики сервера
- **vCPU:** 2
- **RAM:** 4 GB
- **Disk:** SSD 50 GB (app) + 100 GB (DB)
- **IOPS:** 100+

### Конфигурация
| Компонент | Значение |
|-----------|----------|
| Gunicorn workers | 3 (gevent) |
| Celery concurrency | 2 |
| PG max_connections | 50 |
| PG shared_buffers | 1 GB |

### Ожидаемая нагрузка
- Concurrent users (15%): ~495
- Peak RPS: 50-80
- Daily lessons: ~100-200

### Bottleneck
🟡 **RAM** — video processing может вызвать OOM

---

## Stage B: Growth

**Целевая аудитория:** 750 учителей / 7,500 учеников

### Характеристики сервера
- **vCPU:** 4
- **RAM:** 8 GB
- **Disk:** NVMe SSD 100 GB (app) + 250 GB (DB)
- **IOPS:** 500+

### Конфигурация
| Компонент | Значение |
|-----------|----------|
| Gunicorn workers | 5 (gevent) |
| Celery default workers | 2 |
| Celery heavy workers | 1 (отдельный) |
| PG max_connections | 100 |
| PG shared_buffers | 2 GB |
| PgBouncer | ✅ Обязательно |

### Ожидаемая нагрузка
- Concurrent users (15%): ~1,237
- Peak RPS: 120-180
- Daily lessons: ~300-500

### Bottleneck
🟡 **Disk I/O** — частые записи требуют NVMe

### Миграция A → B
1. Установить PgBouncer: `apt install pgbouncer`
2. Настроить `/etc/pgbouncer/pgbouncer.ini` (см. конфиг)
3. Обновить `DATABASE_URL` на порт 6432
4. Применить Stage B systemd services
5. Применить PostgreSQL tuning

---

## Stage C: Scale

**Целевая аудитория:** 1,500 учителей / 15,000 учеников

### Характеристики сервера
- **vCPU:** 8 (или 2×4 с load balancer)
- **RAM:** 16 GB (или 2×8 GB)
- **Disk:** NVMe SSD 200 GB (app) + 500 GB (DB)
- **IOPS:** 3000+ (provisioned)

### Рекомендуемая архитектура
```
                    ┌─────────────┐
                    │   Nginx LB  │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   App #1    │ │   App #2    │ │   Celery    │
    │  (Gunicorn) │ │  (Gunicorn) │ │  (Heavy)    │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────┬───────┴───────┬───────┘
                   │               │
            ┌──────▼──────┐ ┌──────▼──────┐
            │  PgBouncer  │ │    Redis    │
            └──────┬──────┘ └─────────────┘
                   │
            ┌──────▼──────┐
            │ PostgreSQL  │────► Read Replica
            └─────────────┘
```

### Конфигурация
| Компонент | Значение |
|-----------|----------|
| Gunicorn workers | 8 (или 2×4) |
| Celery default workers | 3 |
| Celery heavy workers | 2 (отдельный сервер) |
| PG max_connections | 200 |
| PG shared_buffers | 4 GB |
| PgBouncer | ✅ Обязательно |
| Read Replica | ✅ Рекомендуется |

### Ожидаемая нагрузка
- Concurrent users (15%): ~2,475
- Peak RPS: 250-400
- Daily lessons: ~800-1,500

### Bottleneck
🔴 **CPU** — FFmpeg требует выделенного worker server

### Рекомендации для Stage C
1. **Managed PostgreSQL** (RDS/Cloud SQL) с read replicas
2. **Cloud transcoding** (AWS MediaConvert) вместо локального FFmpeg
3. **Redis Cluster** для высокой доступности Celery
4. **CDN** для статики и записей уроков

---

## Мониторинг

### Ключевые метрики
```bash
# CPU usage
top -bn1 | grep "Cpu(s)"

# Memory
free -h

# PostgreSQL connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Disk IOPS
iostat -x 1 5

# Gunicorn workers
pgrep -f gunicorn | wc -l

# Celery tasks queue
redis-cli llen celery
```

### Алерты (настроить в мониторинге)
| Метрика | Warning | Critical |
|---------|---------|----------|
| CPU % | 70% | 90% |
| Memory % | 80% | 95% |
| Disk % | 80% | 90% |
| PG connections % | 40% | 80% |
| Response time | 500ms | 2000ms |

---

## Стоимость (примерная)

| Stage | Cloud Provider | Ежемесячно |
|-------|----------------|------------|
| A | DigitalOcean 4GB | $24-48 |
| B | DigitalOcean 8GB + managed DB | $120-180 |
| C | AWS/GCP with RDS | $350-500 |

---

## Quick Deploy

```bash
# Посмотреть текущее состояние
./deploy/scaling/monitor-capacity.sh

# Deploy Stage A
sudo ./deploy/scaling/deploy-stage-a.sh

# Deploy Stage B (requires PgBouncer)
sudo apt install pgbouncer
sudo ./deploy/scaling/deploy-stage-b.sh

# Deploy Stage C (requires planning)
sudo ./deploy/scaling/deploy-stage-c.sh
```
