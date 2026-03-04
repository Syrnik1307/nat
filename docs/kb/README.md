# Lectio Space — Knowledge Base (KB)

> Центральная база знаний проекта. Сюда ВСЕ агенты записывают ошибки, решения, инциденты и паттерны. Сюда же они обращаются перед началом работы — чтобы не повторять уже решённые проблемы.

## Структура

```
docs/kb/
├── README.md              ← Вы здесь (правила записи)
├── errors/                ← Ошибки и их решения
│   ├── _index.md          ← Реестр всех ошибок (обновлять!)
│   └── YYYY-MM-DD_slug.md
├── solutions/             ← Найденные решения задач
│   ├── _index.md          ← Реестр решений
│   └── YYYY-MM-DD_slug.md
├── incidents/             ← Инциденты на production
│   ├── _index.md          ← Реестр инцидентов
│   └── YYYY-MM-DD_slug.md
├── deployments/           ← Лог деплоев
│   └── YYYY-MM-DD.md
├── patterns/              ← Паттерны и best practices
│   └── slug.md
└── weekly/                ← Еженедельные сводки
    └── YYYY-WNN.md
```

## Формат записи ошибки (`errors/`)

```markdown
# [Короткое название ошибки]

**Дата**: YYYY-MM-DD
**Severity**: CRITICAL / HIGH / MEDIUM / LOW
**Модуль**: accounts / schedule / homework / frontend / infra
**Агент-автор**: deploy-agent / incident-response / ...
**Теги**: #zoom #oauth #timeout

## Симптомы
Что пользователь или разработчик видит.

## Причина
Техническая root cause.

## Решение
Конкретные шаги или код, которые решили проблему.

## Предотвращение
Что сделано чтобы не повторилось (тест, мониторинг, алерт).

## Связанные файлы
- `path/to/file.py` — что менялось
- `path/to/test.py` — тест на regression
```

## Формат записи решения (`solutions/`)

```markdown
# [Название задачи/фичи]

**Дата**: YYYY-MM-DD
**Сложность**: XS / S / M / L / XL
**Модуль**: accounts / schedule / homework / frontend / infra
**Агент-автор**: backend-api / frontend-qa / ...
**Теги**: #api #payments #ui

## Задача
Что нужно было сделать.

## Подход
Какой подход выбран и почему.

## Реализация
Ключевые изменения (файлы, модели, endpoints).

## Альтернативы (не выбранные)
Другие варианты и почему отклонены.

## Полезно знать
Нюансы, которые пригодятся в будущем.
```

## Формат записи инцидента (`incidents/`)

```markdown
# [INC-NNN] Название инцидента

**Дата**: YYYY-MM-DD HH:MM UTC
**Severity**: SEV1 / SEV2 / SEV3
**Длительность**: X мин / часов
**Агент-автор**: incident-response
**Теги**: #outage #oom #zoom

## Timeline
- HH:MM — Обнаружена проблема (как?)
- HH:MM — Начата диагностика
- HH:MM — Причина найдена
- HH:MM — Fix применён
- HH:MM — Восстановление подтверждено

## Impact
Кого затронуло, сколько пользователей.

## Root Cause
Техническая причина.

## Fix
Что сделано для исправления.

## Action Items
- [ ] Добавить мониторинг на X
- [ ] Написать тест на Y
- [ ] Обновить runbook для Z
```

## Формат лога деплоя (`deployments/`)

```markdown
# Deploy YYYY-MM-DD

**Время**: HH:MM UTC
**Агент**: deploy-agent
**Коммит**: abc1234

## Что задеплоено
- Feature X
- Fix Y
- Update Z

## Миграции
- app/migrations/0042_xxx.py — AddField (безопасно)

## Результат
OK / ROLLBACK

## Post-deploy
- Smoke test: PASS
- Errors: 0
```

## Формат паттерна (`patterns/`)

```markdown
# [Название паттерна]

**Категория**: backend / frontend / devops / architecture
**Теги**: #performance #security #ux

## Проблема
Какую повторяющуюся проблему решает.

## Решение
Паттерн / подход / шаблон кода.

## Примеры в проекте
- `file1.py` — где уже применяется
- `file2.js` — ещё пример

## Антипаттерн
Как НЕ надо делать (и почему).
```

## Правила для агентов

### Обязанность записи
1. **КАЖДЫЙ** агент после завершения задачи проверяет: нужно ли записать в KB?
2. Ошибки/баги → `errors/`
3. Реализованные фичи → `solutions/`
4. Production инциденты → `incidents/`
5. Деплои → `deployments/`
6. Повторяющиеся паттерны → `patterns/`

### Обязанность чтения
1. **ПЕРЕД** началом работы агент проверяет KB:
   - `errors/_index.md` — была ли похожая ошибка?
   - `solutions/_index.md` — решали ли похожую задачу?
   - `patterns/` — есть ли готовый паттерн?
2. Если нашёл релевантную запись — использует как основу, а не изобретает заново.

### Формат имени файла
```
errors/     → YYYY-MM-DD_short-slug.md     (2026-03-04_zoom-oauth-500.md)  
solutions/  → YYYY-MM-DD_short-slug.md     (2026-03-04_finance-filter-api.md)
incidents/  → YYYY-MM-DD_short-slug.md     (2026-03-04_site-down-oom.md)
deployments/→ YYYY-MM-DD.md                (2026-03-04.md)
patterns/   → short-slug.md                (select-related-viewsets.md)
weekly/     → YYYY-WNN.md                  (2026-W10.md)
```

### Обновление индексов
После создания новой записи — добавить строку в `_index.md` соответствующей папки.
