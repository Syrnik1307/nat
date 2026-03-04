# Analytics & Insights Agent — Аналитика и AI-инсайты

## Роль
Ты — дата-аналитик Lectio Space. Работаешь с модулем аналитики, AI-отчётами по успеваемости, heatmaps и поведенческим анализом.

## Модуль Analytics

### Backend (`analytics/`)
| Файл | Назначение |
|------|------------|
| `models.py` | ControlPoint, GradebookEntry, TeacherActivity |
| `views.py` | GradebookViewSet, ControlPointViewSet, teacher stats |
| `ai_analytics_service.py` | AI-генерация отчётов по успеваемости |
| `ai_behavior_service.py` | Поведенческий анализ студентов |
| `extended_analytics_service.py` | Расширенные метрики |
| `signals.py` | Автоматическое создание записей при событиях |
| `teacher_signals.py` | Трекинг активности учителя |

### Frontend
| Компонент | Назначение |
|-----------|------------|
| `AnalyticsPage.js` | Основная страница аналитики учителя |
| `GroupDetailAnalytics.js` | Аналитика по группе |
| `StudentDetailAnalytics.js` | Аналитика по студенту |
| `StudentAnalyticsDashboard.js` | Дашборд студента |
| `StudentAIReports.js` | AI-отчёты для учителя |
| `ActivityHeatmap/` | Heatmap активности |
| `admin/TeacherHeatmapTable.js` | Admin: все учителя |
| `admin/TeacherHeatmapDetail.js` | Admin: детали учителя |

## AI Аналитика

### Отчёт по студенту
```
Входные данные:
- Посещаемость (% за период)
- Оценки за ДЗ (средний балл, тренд)
- Активность (время на платформе)
- Частота пропусков

Выходные данные (AI):
- Общая оценка прогресса
- Сильные стороны
- Зоны роста
- Рекомендации для учителя
- Риск отчисления (low/medium/high)
```

### Поведенческий анализ
```
Метрики:
- Время начала выполнения ДЗ (прокрастинация?)
- Время на выполнение vs среднее
- Паттерны посещаемости (пропуски по дням недели)
- Корреляция посещаемость/оценки
```

## Celery Tasks для аналитики
| Task | Schedule | Purpose |
|------|----------|---------|
| `check_performance_drops` | ежедневно | Уведомление если оценки резко упали |
| `check_group_health` | еженедельно | Общее здоровье группы |
| `check_grading_backlog` | 6 часов | Непроверенные ДЗ > N дней |
| `check_inactive_students` | ежедневно | Студенты без активности > 2 недель |
| `send_student_absence_warnings` | ежедневно | 3+ пропуска подряд |
| `send_student_inactivity_nudges` | еженедельно | Мотивационные сообщения |
| `check_consecutive_absences` | ежедневно | Серии пропусков |

## Gradebook (журнал оценок)
```
Teacher → Group → Students
    └── ControlPoints (контрольные точки)
        └── GradebookEntries (оценки)
            ├── student: FK
            ├── control_point: FK
            ├── grade: float
            ├── comment: str
            └── date: datetime
```

## Finance Analytics (`finance/`)
| Метрика | Описание |
|---------|----------|
| Lesson balance | Баланс уроков студента (оплачено vs проведено) |
| Revenue per teacher | Доход учителя за период |
| Payment history | История оплат и возвратов |
| Weekly revenue report | Еженедельный отчёт (Celery → Telegram) |

## Knowledge Map (feature-flagged)
```
KNOWLEDGE_MAP_ENABLED=1

Модель:
Topic → SubTopic → StudentProgress
├── mastery_level: float (0-1)
├── attempts: int
├── last_activity: datetime
└── recommended_next: FK(Topic)
```

Предоставляет визуальную карту знаний студента с рекомендациями что изучать дальше.
