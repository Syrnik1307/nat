# Реестр ошибок

> Обновляется агентами автоматически. Формат: `| Дата | Slug | Severity | Модуль | Краткое описание |`

| Дата | Файл | Severity | Модуль | Описание |
|------|------|----------|--------|----------|
| 2026-02-08 | [tenant-migration-disaster](../incidents/2026-02-08_tenant-migration-disaster.md) | CRITICAL | all | Мультитенантность сломала ~75 таблиц NOT NULL tenant_id |
| 2026-01 | [gunicorn-oom-sigkill](gunicorn-oom-sigkill.md) | SEV1 | Gunicorn | OOM Kill worker на 2GB VPS |
| 2026-01 | [zoom-oauth-timeout](zoom-oauth-timeout.md) | LOW-MEDIUM | Zoom Pool | Таймаут при прогреве OAuth-токенов |
| 2026-01 | [celerybeat-schedule-corruption](celerybeat-schedule-corruption.md) | MEDIUM | Celery Beat | Повреждение shelve-файла расписания |
| 2026-01 | [ssl-localhost-timeout](ssl-localhost-timeout.md) | LOW | Тесты | HTTPS-запрос к HTTP-серверу |
| 2026-01 | [group-is-active-field-error](group-is-active-field-error.md) | HIGH | accounts/tasks | Фильтрация по несуществующему полю |

<!-- АГЕНТЫ: добавляйте новые записи ВЫШЕ этой строки -->
