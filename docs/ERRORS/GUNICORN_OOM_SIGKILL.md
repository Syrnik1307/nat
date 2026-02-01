# Ошибка: Worker was sent SIGKILL! Perhaps out of memory?

## Симптомы

В Sentry/логах Gunicorn появляется:
```
Worker (pid:689792) was sent SIGKILL! Perhaps out of memory?
```

## Причина

Linux OOM Killer убил процесс из-за нехватки RAM. На сервере с **2 ГБ RAM** это случается когда:

1. **Слишком много workers** — каждый Gunicorn/Celery worker потребляет ~100 МБ
2. **Дублирующие сервисы** — запущены `celery.service` И `celery_worker.service`
3. **Memory limits в systemd** — `MemoryMax=512M` слишком низкий
4. **Утечки памяти** — долгоживущие процессы накапливают память

## Быстрая диагностика

```bash
# Проверить память
free -h

# Топ процессов по памяти
ps aux --sort=-%mem | head -10

# Проверить дублирующие сервисы
sudo systemctl list-units --type=service | grep -E 'celery|gunicorn|teaching'

# Подсчитать worker процессы
pgrep -c gunicorn
pgrep -c celery
```

## Оптимальная конфигурация для 2 ГБ RAM

### Gunicorn (teaching_panel.service):
```
--workers 2          # НЕ 3!
--threads 4
--worker-class gthread
--max-requests 500   # Перезапуск для предотвращения утечек
```

### Celery:
```
--concurrency=1      # 1 worker process
--max-tasks-per-child=100
```

### Итого RAM:
| Компонент | Процессы | RAM |
|-----------|----------|-----|
| Gunicorn master | 1 | ~50 МБ |
| Gunicorn workers | 2 | ~180 МБ |
| Celery worker | 1 | ~100 МБ |
| Celery beat | 1 | ~100 МБ |
| **Итого** | 5 | **~430 МБ** |

Остаётся ~1.5 ГБ для системы, nginx, PostgreSQL, Redis.

## Исправление

```bash
# 1. Остановить дублирующие сервисы
sudo systemctl stop celery_worker celery_beat celery-combined 2>/dev/null
sudo systemctl disable celery_worker celery_beat celery-combined 2>/dev/null

# 2. Убить все лишние процессы
sudo pkill -f celery

# 3. Уменьшить Gunicorn workers до 2
sudo sed -i 's/--workers 3/--workers 2/' /etc/systemd/system/teaching_panel.service
sudo systemctl daemon-reload

# 4. Перезапустить сервисы
sudo systemctl restart teaching_panel celery celery-beat

# 5. Проверить
free -h
pgrep -af 'gunicorn|celery'
```

## Мониторинг

Добавить cron для проверки памяти:

```bash
# /etc/cron.d/memory-check
*/5 * * * * root free -m | awk 'NR==2{if($3/$2*100 > 90) system("systemctl restart teaching_panel")}'
```

## Профилактика

1. **Включить swap** (уже 2 ГБ — хорошо)
2. **max-requests** для автоперезапуска workers
3. **MemoryMax** в systemd не ниже 600M для gunicorn
4. **Один celery worker** с `--concurrency=1`

## FAQ

**Q: Можно ли увеличить workers?**
A: Нет, на 2 ГБ RAM оптимально 2 gunicorn workers + 1 celery worker.

**Q: Почему были дублирующие сервисы?**
A: Разные версии конфигов: `celery.service` и `celery_worker.service` — оба были enabled.

**Q: Как добавить больше capacity?**
A: Увеличить RAM сервера до 4 ГБ, тогда можно 4 gunicorn workers + 2 celery workers.
