# Инцидент: backup_db.sh Permission denied — бэкапы не создавались 6 дней

**Дата:** 2026-03-08 (обнаружено), 2026-03-02 (началось)
**Severity:** P2 (бэкапы не создавались 6 дней, offsite-алерт в Telegram)
**Статус:** Закрыт

## Что произошло

Алерт в Telegram от offsite_backup.sh: "Свежий бэкап БД не найден!"

`backup_db.sh` потерял execute permission (`chmod +x`) после деплоя через `git reset --hard`. Cron получал `Permission denied` и не мог запустить скрипт. Бэкапы не создавались **6 дней** (с ~2 марта по 8 марта).

## Хронология

| Время | Событие |
|---|---|
| ~2026-03-02 | Деплой через `git reset --hard origin/new-prod` сбросил +x на backup_db.sh |
| 2026-03-02 03:00 | Cron: `Permission denied` — старый SQLite-скрипт ещё работал параллельно |
| 2026-03-04 08:54 | Ручной запуск backup_db.sh (с sudo) — создал pg_backup, но +x не восстановили |
| 2026-03-03..08 | Каждую ночь: `Permission denied` x6 в cron.log |
| 2026-03-08 03:30 | offsite_backup.sh не нашёл pg_backup с mtime < 1 день → Telegram алерт |
| 2026-03-08 ~06:30 | Обнаружено и исправлено: `chmod +x`, ручной бэкап PASSED |

## Первопричина

**`git reset --hard` при деплое сбрасывает file permissions на значения из git.**

Git хранит только бит execute (mode 100755 vs 100644). Если файл в репозитории зафиксирован без +x, `git reset --hard` убирает execute permission. На Linux-сервере это критично для cron-скриптов.

## Сопутствующие проблемы

1. **offsite_backup.sh** содержал legacy-ссылку на `db_backup_*.sqlite3.gz` — убрано
2. **backup_db.sh** содержал cleanup для `db_backup_*.sqlite3.gz` — убрано
3. Cron log показывал старый SQLite-скрипт (до 2 марта) — значит backup_db.sh перезаписали при деплое

## Что исправлено

| Файл | Исправление |
|---|---|
| Прод: `backup_db.sh` | `sudo chmod +x` — восстановлено |
| Прод: ручной бэкап | 138 таблиц, 72 юзера, 41 урок — PASSED |
| `deploy_to_production.ps1` | Добавлен `chmod +x *.sh` после каждого `git reset --hard` |
| `offsite_backup.sh` | Убрана legacy-ссылка на `db_backup_*.sqlite3.gz` |
| `backup_db.sh` | Убран cleanup для `db_backup_*.sqlite3.gz` |
| Прод: `/opt/lectio-monitor/offsite_backup.sh` | Синхронизирован новый файл |

## Диагностика (как найти в будущем)

```bash
# 1. Проверить cron log
tail -20 /var/backups/teaching_panel/cron.log

# 2. Проверить offsite log
tail -20 /var/log/lectio-monitor/offsite_backup.log

# 3. Проверить permissions
ls -la /var/www/teaching_panel/teaching_panel/backup_db.sh
# Должно быть: -rwxr-xr-x

# 4. Проверить последние бэкапы
ls -lht /var/backups/teaching_panel/pg_backup_*.sql.gz | head -5

# 5. Ручной запуск для проверки
sudo /var/www/teaching_panel/teaching_panel/backup_db.sh
```

## Уроки

1. **`git reset --hard` сбрасывает chmod** — после ЛЮБОГО деплоя надо восстанавливать +x на shell-скриптах
2. **Алерт приходил от offsite, не от backup** — сам backup_db.sh молча фейлился (cron перехватывал Permission denied в лог)
3. **6 дней без бэкапов** — нужен отдельный алерт "бэкап старше 24ч" в guardian.sh или healthcheck
4. **Legacy SQLite код** — всё ещё находится в разных файлах, надо чистить при каждом обнаружении

## TODO

- [x] Восстановить +x на проде
- [x] Добавить chmod в deploy_to_production.ps1
- [x] Убрать SQLite legacy из offsite_backup.sh и backup_db.sh
- [ ] Добавить проверку "свежий бэкап < 24ч" в guardian.sh (L1 check)
- [ ] Убедиться что git хранит backup_db.sh как mode 100755
