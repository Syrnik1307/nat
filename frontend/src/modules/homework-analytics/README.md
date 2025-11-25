# 📚 Модуль Homework & Analytics

**Ответственный:** Tihon  
**Детальное ТЗ:** [`../../HOMEWORK_MODULE_SPEC.md`](../../HOMEWORK_MODULE_SPEC.md)

## 🎯 Назначение
Система домашних заданий с конструктором вопросов, автопроверкой, мотивационными механиками и аналитикой.

## 📁 Структура папок
```
homework-analytics/
├── components/
│   ├── navigation/        # Внутренний навбар журнала
│   ├── journal/           # Журнал посещений
│   ├── rating/            # Рейтинг студентов
│   ├── homework/          # Управление ДЗ
│   ├── questions/         # Типы вопросов (8 штук)
│   ├── student/           # Интерфейс прохождения
│   ├── gamification/      # Награды, конфетти
│   ├── control-points/    # Контрольные работы
│   └── reports/           # Отчеты и экспорт
├── services/
│   ├── homeworkService.js
│   ├── analyticsService.js
│   └── exportService.js
├── hooks/
│   ├── useHomework.js
│   └── useGamification.js
└── README.md (этот файл)
```

## 🔗 API Endpoints
- `GET /api/homework/`
- `POST /api/homework/`
- `GET /api/submissions/`
- `GET /api/gradebook/`
- `GET /api/teacher-stats/`

## 🚀 Старт разработки
См. подробные промпты в [`HOMEWORK_MODULE_SPEC.md`](../../HOMEWORK_MODULE_SPEC.md)

## ✅ Чеклист (обновлять по мере выполнения)
- [ ] Навигация
- [ ] Журнал и рейтинг
- [ ] Проверка заданий
- [ ] Конструктор (базовые типы)
- [ ] Конструктор (новые типы)
- [ ] Прохождение студентом
- [ ] Мотивационные механики
- [ ] Контрольные точки
- [ ] Отчеты
