# Паттерны и конвенции проекта

## Индекс

### Архитектурные
- [2gb-ram-optimization.md](2gb-ram-optimization.md) — Оптимизация для VPS 2GB RAM
- [celery-task-patterns.md](celery-task-patterns.md) — Паттерны Celery задач

### Запрещённые (Anti-patterns)
- **НИКОГДА**: tenant/multi-tenant код (см. docs/kb/incidents/)
- **НИКОГДА**: emoji в UI (только lucide-react иконки)
- **НИКОГДА**: display:none без анимации (smooth-transitions.css)
- **НИКОГДА**: миграции с DROP без бэкапа
