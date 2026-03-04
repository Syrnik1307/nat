# Homework & AI Grading Agent — Домашние задания и автопроверка

## Роль
Ты — разработчик модуля домашних заданий Lectio Space. Управляешь 8 типами вопросов, AI-автопроверкой и аналитикой по успеваемости.

## Архитектура (homework app)

### Модели
```
HomeworkAssignment (задание)
├── teacher: FK(User)
├── group: FK(Group)
├── title: str
├── questions: JSONField  # 8 типов вопросов
├── time_limit: int (минуты, опционально)
├── deadline: datetime
├── is_active: bool
└── ai_grading_enabled: bool

HomeworkSubmission (ответ ученика)
├── assignment: FK(HomeworkAssignment)
├── student: FK(User)
├── answers: JSONField
├── score: float (0-100)
├── ai_score: float (AI оценка)
├── ai_feedback: JSONField (AI комментарии)
├── teacher_score: float (финальная оценка учителя)
├── status: [submitted, ai_graded, teacher_graded]
├── submitted_at: datetime
└── graded_at: datetime
```

### 8 типов вопросов
| # | Тип | Описание | Автопроверка |
|---|-----|----------|-------------|
| 1 | `single_choice` | Один правильный ответ | Да (exact match) |
| 2 | `multiple_choice` | Несколько правильных | Да (exact match) |
| 3 | `text_input` | Короткий текст | AI |
| 4 | `essay` | Развёрнутый ответ | AI |
| 5 | `matching` | Сопоставление пар | Да (exact match) |
| 6 | `ordering` | Упорядочивание | Да (exact match) |
| 7 | `fill_blanks` | Заполнить пропуски | AI / exact |
| 8 | `file_upload` | Загрузка файла | Только учитель |

### AI Grading Pipeline
```
1. Student submits → HomeworkSubmission created
2. If ai_grading_enabled → добавляется в AIGradingQueue
3. Celery task process_ai_grading_queue (каждые 30 сек):
   a. Берёт batch из очереди (BATCH_SIZE=10)
   b. Для каждого submission:
      - Формирует prompt с вопросом + ответом + критериями
      - Отправляет в Gemini/DeepSeek API
      - Парсит ответ (score, feedback, confidence)
      - Если confidence >= 0.7 → сохраняет ai_score
      - Если confidence < 0.7 → отмечает для ручной проверки
4. Teacher reviews AI grades → approves/adjusts → teacher_score
```

### Feature Flags
```python
AI_GRADING_ENABLED = os.environ.get('AI_GRADING_ENABLED', '0') == '1'
AI_GRADING_GEMINI_MODEL = 'gemini-2.0-flash'
AI_GRADING_CONFIDENCE_THRESHOLD = 0.7
AI_GRADING_QUEUE_BATCH_SIZE = 10
```

## Ключевые файлы

### Backend
| Файл | Назначение |
|------|------------|
| `homework/models.py` | HomeworkAssignment, HomeworkSubmission, AIGradingQueue |
| `homework/views.py` | CRUD заданий, submission, grading |
| `homework/serializers.py` | Сериализация вопросов и ответов |
| `homework/ai_grading_service.py` | AI grading logic (Gemini/DeepSeek) |
| `homework/tasks.py` | process_ai_grading_queue, reset_daily_usage |

### Frontend
| Файл | Назначение |
|------|------------|
| `modules/homework-analytics/components/HomeworkPage.js` | Конструктор ДЗ (учитель) |
| `modules/homework-analytics/components/homework/HomeworkTake.js` | Выполнение ДЗ (ученик) |
| `modules/homework-analytics/components/homework/HomeworkAnswersView.js` | Просмотр ответов |
| `modules/homework-analytics/components/teacher/SubmissionsList.js` | Список сдач |
| `modules/homework-analytics/components/teacher/SubmissionReview.js` | Проверка учителем |

## API Endpoints
```
GET    /api/homework/assignments/           # Список заданий
POST   /api/homework/assignments/           # Создать задание
GET    /api/homework/assignments/{id}/      # Детали задания
PUT    /api/homework/assignments/{id}/      # Обновить
DELETE /api/homework/assignments/{id}/      # Удалить

POST   /api/homework/submissions/           # Отправить ответ
GET    /api/homework/submissions/           # Список ответов
GET    /api/homework/submissions/{id}/      # Детали ответа
POST   /api/homework/submissions/{id}/grade/ # Оценить (учитель)
```

## AI Grading Мониторинг
```python
# Celery tasks для мониторинга
'check-ai-pool-capacity'   # каждый час — проверка лимитов API
'reset-daily-api-key-usage' # ежедневно 00:05 — сброс счётчиков
'send-ai-usage-weekly-report' # пн 09:30 — отчёт по использованию
```
