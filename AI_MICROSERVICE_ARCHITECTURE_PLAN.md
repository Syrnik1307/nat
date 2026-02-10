# AI Grading Microservice — Архитектурный план интеграции

> **Дата**: 10 февраля 2026
> **Версия**: 1.0
> **Статус**: Draft → Review
> **Автор**: Senior Backend Architect

---

## Содержание

1. [Анализ текущего состояния](#1-анализ-текущего-состояния)
2. [Целевая архитектура](#2-целевая-архитектура)
3. [Схема потоков данных](#3-схема-потоков-данных)
4. [API-контракт](#4-api-контракт)
5. [Стратегия отказоустойчивости](#5-стратегия-отказоустойчивости)
6. [Безопасность](#6-безопасность)
7. [План разработки (бэкенд)](#7-план-разработки-бэкенд)
8. [Мониторинг и SLA](#8-мониторинг-и-sla)
9. [Миграционный путь от монолита](#9-миграционный-путь-от-монолита)

---

## 1. Анализ текущего состояния

### Что уже есть

| Компонент | Файл | Состояние |
|-----------|-------|-----------|
| **Базовый AI сервис** | `homework/ai_grading_service.py` | Синхронный HTTP-вызов DeepSeek/OpenAI внутри Django process |
| **Экзаменационный AI сервис** | `homework/exam_ai_grading_service.py` | Синхронный HTTP-вызов + кэш Redis, критерии ФИПИ |
| **AI-вызов из модели** | `homework/models.py` → `Answer._evaluate_with_ai()` | Вызывается **синхронно** внутри `Answer.evaluate()` |
| **Celery-инфраструктура** | `settings.py`, 4 очереди | Развитая, но AI-задачи **не используют** Celery |
| **Модели данных** | `Answer.auto_score`, `teacher_feedback`, `needs_manual_review` | Нет выделенных полей для AI-метаданных |

### Ключевые проблемы текущей архитектуры

1. **Blocking request** — `_evaluate_with_ai()` вызывается синхронно внутри Django request cycle (5-10 сек блокировки gunicorn worker)
2. **Связанность** — AI-логика встроена прямо в слой модели (`Answer.evaluate()`)
3. **Нет изоляции отказа** — если DeepSeek API зависнет на 30 сек, gunicorn worker заблокирован, при массовой проверке сервер упадёт
4. **Нет раздельного масштабирования** — нельзя добавить AI workers отдельно от web workers
5. **Нет аудит-лога** — нет трекинга стоимости, токенов, latency AI-вызовов

---

## 2. Целевая архитектура

### Принцип: **Strangler Fig Pattern**

Не заменяем всё разом, а постепенно перенаправляем AI-вызовы в микросервис, сохраняя fallback на in-process для простых проверок.

### Компоненты

```
┌───────────────────────────────────────────────────────────────────┐
│                       МОНОЛИТ (Django)                            │
│                                                                   │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────────────┐ │
│  │  Views    │───▶│ Answer       │───▶│ AI Gateway Client       │ │
│  │ (submit) │    │ .evaluate()  │    │ (enqueue + return 202)  │ │
│  └──────────┘    └──────────────┘    └──────────┬──────────────┘ │
│                                                  │                │
│  ┌──────────────────────────┐                    │                │
│  │ Callback Handler         │◀───── webhook ─────┘                │
│  │ POST /api/internal/      │                                     │
│  │   ai-grading/callback/   │                                     │
│  └──────────────────────────┘                                     │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                     Redis (Broker)
                     Queue: ai_grading
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│                  AI GRADING MICROSERVICE                          │
│                                                                   │
│  ┌───────────────┐    ┌─────────────┐    ┌────────────────────┐  │
│  │ Queue Consumer │───▶│ Grading     │───▶│ AI Provider Client │  │
│  │ (Celery/ARQ)  │    │ Orchestrator│    │ DeepSeek / OpenAI  │  │
│  └───────────────┘    └──────┬──────┘    └────────────────────┘  │
│                              │                                    │
│                       ┌──────▼──────┐                             │
│                       │ Result      │    ┌────────────────────┐   │
│                       │ Publisher   │───▶│ Callback to Django  │   │
│                       │             │    │ (HTTP + HMAC sig)   │   │
│                       └──────┬──────┘    └────────────────────┘   │
│                              │                                    │
│                       ┌──────▼──────┐                             │
│                       │ Postgres/   │  ← audit log, costs,       │
│                       │ SQLite (own)│    prompt versions          │
│                       └─────────────┘                             │
└───────────────────────────────────────────────────────────────────┘
```

### Почему именно так

| Решение | Альтернатива | Почему выбрано |
|---------|-------------|----------------|
| **Redis Queue** (существующий) | Kafka, RabbitMQ | Уже используется (Celery broker); минимум нового инфра |
| **Callback (webhook)** | Polling, WebSocket | Простота; монолит уже умеет принимать webhooks (YooKassa) |
| **Отдельный процесс** | Lambda/Cloud Functions | Контроль, отладка, нет vendor lock-in |
| **Celery worker** | Собственный consumer (ARQ/Dramatiq) | Единая инфраструктура мониторинга; уже 4 очереди |

---

## 3. Схема потоков данных

### 3.1. Основной поток: Отправка задания на проверку

```
 Студент                 Django Monolith                Redis           AI Microservice         DeepSeek API
    │                         │                           │                    │                      │
    │  POST /submissions/     │                           │                    │                      │
    │  {answers: [...]}       │                           │                    │                      │
    │────────────────────────▶│                           │                    │                      │
    │                         │                           │                    │                      │
    │                         │ 1. Сохранить ответы       │                    │                      │
    │                         │    Answer.evaluate()      │                    │                      │
    │                         │    (auto-check для        │                    │                      │
    │                         │     SINGLE/MULTI_CHOICE)  │                    │                      │
    │                         │                           │                    │                      │
    │                         │ 2. TEXT-ответы с           │                    │                      │
    │                         │    ai_grading_enabled:    │                    │                      │
    │                         │    → Поставить в очередь  │                    │                      │
    │                         │                           │                    │                      │
    │                         │──LPUSH ai_grading────────▶│                    │                      │
    │                         │                           │                    │                      │
    │  202 Accepted           │                           │                    │                      │
    │  {status: "checking",   │                           │                    │                      │
    │   grading_job_id: "..."}│                           │                    │                      │
    │◀────────────────────────│                           │                    │                      │
    │                         │                           │                    │                      │
    │                         │                           │──BRPOP────────────▶│                      │
    │                         │                           │                    │                      │
    │                         │                           │                    │ 3. Формирует промпт   │
    │                         │                           │                    │    + retry logic      │
    │                         │                           │                    │                      │
    │                         │                           │                    │──POST /chat/compl.───▶│
    │                         │                           │                    │                      │
    │                         │                           │                    │◀───JSON response──────│
    │                         │                           │                    │                      │
    │                         │                           │                    │ 4. Парсит результат,  │
    │                         │                           │                    │    сохраняет audit    │
    │                         │                           │                    │                      │
    │                         │  5. POST /api/internal/   │                    │                      │
    │                         │     ai-grading/callback/  │                    │                      │
    │                         │◀─────────────────────────────────────HMAC──────│                      │
    │                         │                           │                    │                      │
    │                         │ 6. Обновить Answer:       │                    │                      │
    │                         │    auto_score, feedback   │                    │                      │
    │                         │    needs_manual_review    │                    │                      │
    │                         │                           │                    │                      │
    │                         │ 7. Notify student         │                    │                      │
    │                         │    (Telegram/email)       │                    │                      │
    │                         │                           │                    │                      │
```

### 3.2. Проверка статуса (polling от фронтенда)

```
Фронтенд              Django
   │                     │
   │ GET /submissions/   │
   │    {id}/status/     │
   │────────────────────▶│
   │                     │── Читает Answer из БД
   │                     │
   │ {status: "checked", │
   │  score: 8,          │
   │  feedback: "..."}   │
   │◀────────────────────│
```

### 3.3. Batch-проверка (учитель запускает AI проверку всего класса)

```
Учитель               Django                    Redis              AI Microservice
   │                     │                         │                      │
   │ POST /homework/     │                         │                      │
   │  {id}/ai-grade-all/ │                         │                      │
   │────────────────────▶│                         │                      │
   │                     │                         │                      │
   │                     │── Собрать все TEXT       │                      │
   │                     │   answers без оценки    │                      │
   │                     │                         │                      │
   │                     │   Для каждого answer:   │                      │
   │                     │──LPUSH ai_grading──────▶│                      │
   │                     │                         │                      │
   │ 202 Accepted        │                         │──Обработка по────────▶│
   │ {queued: 25,        │                         │  одному из очереди   │
   │  estimated_time:    │                         │                      │
   │  "~3 мин"}          │                         │                      │
   │◀────────────────────│                         │                      │
```

---

## 4. API-контракт

### 4.1. Монолит → Очередь (Task payload)

```json
{
  "task_id": "grade_550e8400-e29b-41d4-a716-446655440000",
  "version": "1",
  "created_at": "2026-02-10T12:00:00Z",
  "callback_url": "https://lectiospace.ru/api/internal/ai-grading/callback/",
  
  "grading_request": {
    "answer_id": 12345,
    "submission_id": 678,
    "homework_id": 42,
    "question_type": "TEXT",
    
    "question": {
      "prompt": "Объясните принцип работы рекурсии на примере факториала",
      "max_points": 10,
      "correct_answer": "Рекурсия — вызов функции самой себя с уменьшением задачи...",
      "subject_context": "Информатика, 10 класс"
    },
    
    "student_answer": {
      "text": "Рекурсия это когда функция вызывает саму себя. Например factorial(n) = n * factorial(n-1), а factorial(1) = 1.",
      "attachments": []
    },
    
    "grading_config": {
      "provider": "deepseek",
      "model": "deepseek-chat",
      "custom_prompt": null,
      "exam_mode": null,
      "language": "ru"
    }
  }
}
```

### 4.2. AI Микросервис → Монолит (Callback)

**Успешная проверка:**

```json
{
  "task_id": "grade_550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "completed_at": "2026-02-10T12:00:07Z",
  
  "result": {
    "answer_id": 12345,
    "score": 8,
    "max_points": 10,
    "confidence": 0.85,
    "feedback": "Правильно описан принцип рекурсии и приведён корректный пример с факториалом. Не раскрыто понятие базового случая рекурсии как обязательного условия завершения. Рекомендую дополнить ответ описанием стека вызовов.",
    "needs_manual_review": false,
    
    "ai_metadata": {
      "provider": "deepseek",
      "model": "deepseek-chat",
      "input_tokens": 342,
      "output_tokens": 128,
      "cost_rubles": 0.0015,
      "latency_ms": 6840,
      "prompt_version": "v2.1"
    }
  },
  
  "signature": "hmac-sha256:a1b2c3d4e5f6..."
}
```

**Ошибка проверки (graceful degradation):**

```json
{
  "task_id": "grade_550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "completed_at": "2026-02-10T12:01:30Z",
  
  "error": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "DeepSeek API returned 503 after 3 retries",
    "retries_attempted": 3,
    "last_retry_at": "2026-02-10T12:01:28Z",
    "should_retry_later": true
  },
  
  "fallback": {
    "answer_id": 12345,
    "needs_manual_review": true,
    "feedback": "[AI недоступен] Требуется ручная проверка"
  },
  
  "signature": "hmac-sha256:f6e5d4c3b2a1..."
}
```

### 4.3. Экзаменационный режим (ЕГЭ/ОГЭ) — Расширенный контракт

**Запрос:**

```json
{
  "task_id": "exam_grade_...",
  "version": "1",
  "callback_url": "https://lectiospace.ru/api/internal/ai-grading/callback/",
  
  "grading_request": {
    "answer_id": 12345,
    "question_type": "TEXT",
    
    "question": {
      "prompt": "Напишите сочинение по прочитанному тексту...",
      "max_points": 25,
      "source_text": "Текст для исходного материала (до 500 слов)..."
    },
    
    "student_answer": {
      "text": "Текст сочинения ученика..."
    },
    
    "grading_config": {
      "provider": "deepseek",
      "model": "deepseek-chat",
      "exam_mode": {
        "type": "EGE",
        "subject": "russian",
        "task_code": "27",
        "criteria_key": "russian_27",
        "year": 2026
      }
    }
  }
}
```

**Ответ (экзамен):**

```json
{
  "task_id": "exam_grade_...",
  "status": "completed",
  
  "result": {
    "answer_id": 12345,
    "score": 19,
    "max_points": 25,
    "confidence": 0.78,
    "needs_manual_review": true,
    
    "criteria_scores": {
      "K1": { "score": 1, "max": 1, "name": "Формулировка проблемы", "reasoning": "Проблема сформулирована верно" },
      "K2": { "score": 5, "max": 6, "name": "Комментарий к проблеме", "reasoning": "Два примера-иллюстрации, но связь между ними слабо обоснована" },
      "K3": { "score": 1, "max": 1, "name": "Позиция автора", "reasoning": "Позиция определена верно" },
      "K4": { "score": 1, "max": 1, "name": "Отношение к позиции", "reasoning": "Собственная позиция аргументирована" },
      "K5": { "score": 2, "max": 2, "name": "Смысловая цельность", "reasoning": "Текст логичен" },
      "K6": { "score": 2, "max": 2, "name": "Точность и выразительность", "reasoning": "Речь разнообразна" },
      "K7": { "score": 3, "max": 3, "name": "Орфография", "reasoning": "Ошибок нет" },
      "K8": { "score": 2, "max": 3, "name": "Пунктуация", "reasoning": "1 пунктуационная ошибка" },
      "K9": { "score": 1, "max": 2, "name": "Грамматика", "reasoning": "1 грамматическая ошибка в согласовании" },
      "K10": { "score": 1, "max": 2, "name": "Речевые нормы", "reasoning": "Повтор слова 'поэтому' (3 раза)" },
      "K11": { "score": 0, "max": 1, "name": "Этические нормы", "reasoning": "Нарушений нет" },
      "K12": { "score": 0, "max": 1, "name": "Фактологическая точность", "reasoning": "ОК" }
    },
    
    "feedback": "Сочинение в целом хорошее...",
    "strengths": ["Чёткая формулировка проблемы", "Хорошая аргументация"],
    "weaknesses": ["Слабая связь между примерами в K2", "Повторы в речи"],
    "examples_of_errors": [
      { "type": "пунктуация", "fragment": "Однако автор считает что...", "correction": "Однако автор считает, что..." }
    ],
    
    "ai_metadata": {
      "provider": "deepseek",
      "model": "deepseek-chat",
      "input_tokens": 2100,
      "output_tokens": 850,
      "cost_rubles": 0.0051,
      "latency_ms": 12400,
      "prompt_version": "ege_russian_27_v3"
    }
  }
}
```

### 4.4. REST API (Django) — Новые эндпоинты

| Метод | URL | Назначение |
|-------|-----|-----------|
| `POST` | `/api/homework/{id}/ai-grade-all/` | Учитель: запустить AI-проверку всех непроверенных TEXT-ответов |
| `GET` | `/api/submissions/{id}/grading-status/` | Фронтенд: polling статуса проверки |
| `POST` | `/api/internal/ai-grading/callback/` | Микросервис → монолит: приём результатов (HMAC auth) |
| `GET` | `/api/ai-grading/stats/` | Админ: статистика вызовов, стоимость, latency |
| `POST` | `/api/ai-grading/retry/{task_id}/` | Админ: повторная отправка в очередь |

---

## 5. Стратегия отказоустойчивости

### 5.1. Circuit Breaker (Предохранитель)

```
Состояния:
  CLOSED (норма) ──3 ошибки подряд──▶ OPEN (блокировка)
                                          │
                                     30 сек cooldown
                                          │
                                     HALF-OPEN (пробный запрос)
                                       │           │
                                    успех        ошибка
                                       │           │
                                    CLOSED        OPEN
```

**Реализация в микросервисе:**

```python
class CircuitBreaker:
    """
    Конфигурация:
    - failure_threshold: 3 (ошибки до размыкания)
    - recovery_timeout: 30 сек (время остывания)
    - half_open_max_calls: 1 (пробных запросов)
    """
    
    # При OPEN → запись идёт в DLQ, Answer.needs_manual_review = True
    # При HALF-OPEN → 1 пробный запрос, если OK → CLOSED
```

### 5.2. Retry Policy (Политика повторов)

```
Попытка 1 → ошибка → ждём 2 сек
Попытка 2 → ошибка → ждём 4 сек  
Попытка 3 → ошибка → ждём 8 сек
→ ОТКАЗ → запись в Dead Letter Queue
```

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| `max_retries` | 3 | Больше бессмысленно при 503 |
| `backoff` | Exponential (2^n сек) | Не DDoS-им провайдера |
| `jitter` | ± 500ms | Разносим retry при batch |
| `retry_on` | HTTP 429, 500, 502, 503, 504, `ConnectionError`, `Timeout` | Только transient ошибки |
| `no_retry_on` | HTTP 400, 401, 403 | Bad request — нет смысла повторять |

### 5.3. Dead Letter Queue (DLQ)

```
ai_grading (основная очередь)
     │
     │── 3 fail → ai_grading_dlq (Dead Letter Queue)
                      │
                      ├── Хранится 7 дней
                      ├── Alert в Telegram если DLQ > 10
                      └── Ручной retry через admin API
```

**Что попадает в DLQ:**
- Задания, у которых исчерпаны все retry
- Задания с невалидным payload (parse error)
- Задания, отклонённые Circuit Breaker

**Автоматика при DLQ:**
1. `Answer.needs_manual_review = True`
2. `Answer.teacher_feedback = "[AI недоступен] Требуется ручная проверка"`
3. Telegram-алерт учителю: "AI не смог проверить N ответов, проверьте вручную"

### 5.4. Таймауты

| Этап | Таймаут | Действие при превышении |
|------|---------|------------------------|
| Redis enqueue | 5 сек | 500 Internal, логируем |
| AI Provider HTTP | 30 сек | Retry |
| Callback HTTP | 10 сек | Retry callback, не retry AI |
| Celery task visibility | 60 мин | Re-enqueue (worker died) |

### 5.5. Graceful Degradation (карта состояний)

```
                  ┌─────────────────────────┐
                  │  AI Provider доступен?   │
                  └────────┬────────────────┘
                     Да    │    Нет
                     ▼     │    ▼
              ┌────────┐   │  ┌──────────────────────────┐
              │ Норма  │   │  │ Circuit Breaker OPEN?    │
              │ (AI)   │   │  └──────┬───────────────────┘
              └────────┘   │     Да  │  Нет (HALF-OPEN)
                           │     ▼   │    ▼
                           │  ┌──────────┐  ┌──────────┐
                           │  │ DLQ +    │  │ 1 пробный│
                           │  │ manual   │  │ запрос   │
                           │  │ review   │  └──────────┘
                           │  └──────────┘
```

### 5.6. Provider Failover

```python
PROVIDER_CHAIN = [
    {"provider": "deepseek", "model": "deepseek-chat"},        # Primary (дешёвый)
    {"provider": "openai",  "model": "gpt-4o-mini"},           # Fallback (дороже, но надёжнее)
]

# Если primary 3x fail → автоматически переключается на fallback
# При fallback стоимость выше → alert админу
```

---

## 6. Безопасность

### 6.1. Передача данных

| Канал | Защита |
|-------|--------|
| Монолит → Redis | Redis ACL + TLS (в production), пароль в `CELERY_BROKER_URL` |
| Redis → Микросервис | Тот же Redis, тот же network namespace |
| Микросервис → AI Provider | HTTPS (TLS 1.3), API key в header |
| Микросервис → Монолит (callback) | HTTPS + HMAC-SHA256 signature |

### 6.2. HMAC Callback Verification

```python
# Микросервис: подписывает payload
import hmac, hashlib

def sign_callback(payload: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()

# Монолит: верифицирует подпись
def verify_callback(request):
    signature = request.headers.get("X-AI-Signature")
    expected = sign_callback(request.body, settings.AI_CALLBACK_SECRET)
    if not hmac.compare_digest(signature, expected):
        return Response(status=403)
```

### 6.3. Минимизация данных

Мы **НЕ передаём** AI-провайдеру:
- Имя/фамилию студента
- Email, телефон  
- ID студента в системе  

В промпт попадает **только**:
- Текст вопроса
- Ответ студента
- Эталонный ответ (если есть)
- Контекст от преподавателя

### 6.4. Сетевая изоляция

```
                 ┌──── Public Internet ────┐
                 │                         │
                 │    DeepSeek/OpenAI API   │
                 │                         │
                 └────────▲────────────────┘
                          │ HTTPS (443)
                          │
          ┌───────────────┼───────────────────┐
          │  Private VNet / Docker Network    │
          │                                    │
          │  ┌─────────┐    ┌──────────────┐  │
          │  │ Django   │◀──▶│ Redis        │  │
          │  │ (monolith│    │ (no public   │  │
          │  │  :8000)  │    │  access)     │  │
          │  └─────────┘    └──────┬───────┘  │
          │                        │           │
          │                 ┌──────▼───────┐   │
          │                 │ AI Grading   │   │
          │                 │ Worker       │   │
          │                 │ (no public   │   │
          │                 │  access)     │   │
          │                 └──────────────┘   │
          └────────────────────────────────────┘
```

AI Grading worker **не имеет** входящего публичного доступа. Единственные исходящие соединения:
- Redis (внутренняя сеть)
- AI Provider API (HTTPS)
- Django callback (внутренняя сеть или loopback)

### 6.5. Секреты

| Секрет | Хранение | Ротация |
|--------|----------|---------|
| `DEEPSEEK_API_KEY` | Env var, **не в коде** | По требованию |
| `OPENAI_API_KEY` | Env var | По требованию |
| `AI_CALLBACK_SECRET` | Env var (shared secret) | Ежемесячно |
| `REDIS_PASSWORD` | Env var | При компрометации |

---

## 7. План разработки (бэкенд)

### Этап 0: Подготовка (1-2 дня)

- [ ] Создать ветку `feature/ai-grading-microservice`
- [ ] Добавить в `settings.py` новые конфиг-переменные:
  ```python
  AI_GRADING_ASYNC = bool(os.environ.get('AI_GRADING_ASYNC', '0'))
  AI_CALLBACK_SECRET = os.environ.get('AI_CALLBACK_SECRET', 'dev-secret-change-me')
  AI_GRADING_QUEUE = 'ai_grading'
  AI_GRADING_DLQ = 'ai_grading_dlq'
  AI_GRADING_MAX_RETRIES = 3
  AI_GRADING_TIMEOUT = 30
  ```
- [ ] Добавить очередь `ai_grading` в `CELERY_TASK_QUEUES`
- [ ] Создать миграцию: поля `grading_job_id` (UUID, nullable), `ai_grading_status` (enum: pending/processing/completed/failed, default null) на `Answer`

### Этап 1: AI Gateway Client в монолите (2-3 дня)

**Цель**: Создать прослойку, которая решает куда отправить — синхронно (старый путь) или асинхронно (новый путь).

- [ ] `homework/ai_gateway.py` — класс `AIGradingGateway`:
  ```python
  class AIGradingGateway:
      def submit_for_grading(self, answer: Answer, homework: Homework) -> str:
          """
          Returns: grading_job_id (UUID)
          
          If AI_GRADING_ASYNC:
              → Celery task → Redis queue
          Else:
              → Синхронный вызов (текущее поведение, fallback)
          """
  ```
- [ ] Рефакторинг `Answer._evaluate_with_ai()` → вызов `AIGradingGateway.submit_for_grading()`
- [ ] Celery task `homework/tasks.py::enqueue_ai_grading` — кладёт payload в Redis
- [ ] Unit-тесты для gateway (mock Redis)

### Этап 2: Callback endpoint в монолите (1-2 дня)

- [ ] `homework/ai_callback_views.py` — обработчик callback от микросервиса:
  ```python
  @api_view(['POST'])
  @permission_classes([])  # No JWT — HMAC auth instead
  def ai_grading_callback(request):
      verify_hmac(request)
      result = request.data
      
      answer = Answer.objects.get(id=result['result']['answer_id'])
      answer.auto_score = result['result']['score']
      answer.teacher_feedback = format_ai_feedback(result['result'])
      answer.needs_manual_review = result['result']['needs_manual_review']
      answer.ai_grading_status = 'completed'
      answer.save()
      
      # Уведомление
      notify_student_graded.delay(answer.submission.id)
  ```
- [ ] URL: `POST /api/internal/ai-grading/callback/`
- [ ] HMAC verification middleware
- [ ] Integration test: mock callback → проверить обновление Answer

### Этап 3: AI Grading Worker (3-4 дня)

**Цель**: Отдельный Celery worker, который забирает задачи из `ai_grading` и обрабатывает.

- [ ] Создать `ai_grading_worker/` (отдельная директория или Django app):
  ```
  ai_grading_worker/
  ├── __init__.py
  ├── celery_app.py      # Отдельный Celery app (или shared)
  ├── tasks.py           # process_grading_task
  ├── providers/
  │   ├── __init__.py
  │   ├── base.py        # AbstractAIProvider
  │   ├── deepseek.py    # DeepSeekProvider
  │   └── openai.py      # OpenAIProvider
  ├── circuit_breaker.py # CircuitBreaker (Redis-backed state)
  ├── retry_policy.py    # RetryPolicy with exponential backoff
  ├── prompt_registry.py # Versioned prompts (text, EGE, OGE)
  ├── audit.py           # AuditLogger (costs, latency, tokens)
  └── tests/
  ```
- [ ] `tasks.py::process_grading_task` — основная логика:
  1. Десериализовать payload
  2. Выбрать provider (circuit breaker check)
  3. Сформировать prompt (из prompt_registry)
  4. Вызвать AI provider (с retry policy)
  5. Парсить ответ
  6. Записать audit log
  7. Отправить callback в монолит
- [ ] Provider failover: deepseek → openai
- [ ] Dead Letter Queue routing при исчерпании retries

### Этап 4: Batch-проверка и REST API (2 дня)

- [ ] `HomeworkViewSet.ai_grade_all()` — action для массовой AI-проверки
- [ ] `StudentSubmissionViewSet.grading_status()` — endpoint для polling
- [ ] Rate limiting: max 100 заданий в batch, max 500/час на учителя
- [ ] Estimation endpoint: `POST /api/ai-grading/estimate/` — сколько будет стоить проверка N работ

### Этап 5: Мониторинг и алерты (1-2 дня)

- [ ] Telegram-алерты: DLQ > 10, circuit breaker OPEN, cost > threshold
- [ ] Django Admin: страница `AI Grading Audit Log` (список проверок, timestamps, стоимость)
- [ ] Prometheus-метрики (опционально):
  - `ai_grading_requests_total` (counter, label: provider, status)
  - `ai_grading_latency_seconds` (histogram)
  - `ai_grading_cost_rubles_total` (counter)
  - `ai_grading_queue_depth` (gauge)

### Этап 6: Интеграционное тестирование и деплой (2-3 дня)

- [ ] End-to-end тест: сабмит → enqueue → worker → callback → проверить Answer
- [ ] Load test: 50 одновременных проверок, убедиться что монолит не тормозит
- [ ] Feature flag `AI_GRADING_ASYNC=0` на production → постепенное включение
- [ ] Запуск отдельного Celery worker: `celery -A teaching_panel worker -Q ai_grading -c 4 --max-tasks-per-child=20`
- [ ] Документация для деплой-скрипта

### Временная оценка

| Этап | Время | Зависимости |
|------|-------|-------------|
| 0. Подготовка | 1-2 дня | - |
| 1. Gateway Client | 2-3 дня | Этап 0 |
| 2. Callback Endpoint | 1-2 дня | Этап 0 |
| 3. Worker | 3-4 дня | Этап 1 + 2 |
| 4. Batch API | 2 дня | Этап 3 |
| 5. Мониторинг | 1-2 дня | Этап 3 |
| 6. Тестирование + деплой | 2-3 дня | Всё |
| **Итого** | **12-16 дней** | |

Этапы 1 и 2 параллелизуемы. Этапы 4 и 5 параллелизуемы.

**Критический путь**: 0 → 1 → 3 → 6 = **8-12 дней**.

---

## 8. Мониторинг и SLA

### SLA микросервиса

| Метрика | Target | Alarm |
|---------|--------|-------|
| Доступность (uptime) | 99.5% | < 99% → Telegram alert |
| P95 latency (AI call) | < 15 сек | > 20 сек → alert |
| Ошибки (error rate) | < 5% | > 10% → circuit breaker |
| DLQ depth | 0 | > 10 → alert |
| Queue depth | < 100 | > 500 → scale warning |

### Мониторинг-dashboard (Telegram бот)

```
/ai_status → 
  AI Grading Service Status
  ─────────────────────────
  Circuit Breaker: CLOSED
  Queue depth: 3
  DLQ depth: 0
  Last 1h: 47 checks, 0 errors
  Avg latency: 6.2s
  Cost today: 0.42 RUB
  Provider: deepseek (primary)
```

---

## 9. Миграционный путь от монолита

### Фаза 1: Shadow Mode (неделя 1-2)

```
Answer.evaluate() → if TEXT:
    if AI_GRADING_ASYNC:
        → Gateway → Queue → Worker → Callback  (НОВЫЙ ПУТЬ)
    else:
        → _evaluate_with_ai()  (СТАРЫЙ ПУТЬ, default)
```

- Feature flag `AI_GRADING_ASYNC=0` по умолчанию
- Включаем для одного учителя-пилота
- Сравниваем результаты (score, latency)

### Фаза 2: Gradual Rollout (неделя 3)

- `AI_GRADING_ASYNC=1` для всех
- Старый синхронный путь остаётся как fallback
- Мониторим queue depth, latency, error rate

### Фаза 3: Cleanup (неделя 4+)

- Удалить `_evaluate_with_ai()` из `Answer` модели
- Удалить прямые зависимости от `httpx` в homework app
- AI Gateway становится единственным путём

---

## Приложение A: Конфигурация Celery (дополнение к settings.py)

```python
# === AI GRADING ===
AI_GRADING_ASYNC = bool(os.environ.get('AI_GRADING_ASYNC', '0'))
AI_CALLBACK_SECRET = os.environ.get('AI_CALLBACK_SECRET', 'dev-secret-change-me')
AI_GRADING_MAX_RETRIES = int(os.environ.get('AI_GRADING_MAX_RETRIES', '3'))
AI_GRADING_TIMEOUT = int(os.environ.get('AI_GRADING_TIMEOUT', '30'))

# Добавить к CELERY_TASK_QUEUES:
from kombu import Queue
CELERY_TASK_QUEUES += (
    Queue('ai_grading', routing_key='ai_grading'),
    Queue('ai_grading_dlq', routing_key='ai_grading_dlq'),
)

# Добавить к CELERY_TASK_ROUTES:
CELERY_TASK_ROUTES.update({
    'homework.tasks.process_ai_grading': {'queue': 'ai_grading'},
    'homework.tasks.process_ai_grading_dlq': {'queue': 'ai_grading_dlq'},
})
```

## Приложение B: Запуск worker-ов

```bash
# Основной web (без AI очереди):
celery -A teaching_panel worker -Q default,heavy,notifications,periodic -c 4

# AI Grading worker (отдельный процесс, можно на другом сервере):
celery -A teaching_panel worker -Q ai_grading -c 4 \
    --max-tasks-per-child=20 \
    --soft-time-limit=60 \
    --time-limit=120 \
    -n ai_worker@%h

# DLQ processor (ручной или периодический):
celery -A teaching_panel worker -Q ai_grading_dlq -c 1 \
    -n dlq_worker@%h
```

## Приложение C: Миграция БД

```python
# homework/migrations/XXXX_add_ai_grading_fields.py

from django.db import migrations, models
import uuid

class Migration(migrations.Migration):
    dependencies = [
        ('homework', 'XXXX_previous'),
    ]

    operations = [
        # Все поля nullable → безопасная миграция
        migrations.AddField(
            model_name='answer',
            name='grading_job_id',
            field=models.UUIDField(null=True, blank=True, db_index=True),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_grading_status',
            field=models.CharField(
                max_length=20, null=True, blank=True,
                choices=[
                    ('pending', 'В очереди'),
                    ('processing', 'Проверяется'),
                    ('completed', 'Проверено'),
                    ('failed', 'Ошибка'),
                ],
            ),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_provider_used',
            field=models.CharField(max_length=30, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_cost_rubles',
            field=models.DecimalField(
                max_digits=8, decimal_places=4, null=True, blank=True
            ),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_latency_ms',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_tokens_used',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_checked_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
```

> Все поля `null=True` → **безопасная миграция**, данные не затрагиваются.

---

**Итог**: Архитектура обеспечивает полную изоляцию AI-проверки от основного сервиса, асинхронную обработку, многоуровневую отказоустойчивость и безопасную передачу данных. Планы разработки позволяют начать работу без фронтенд-зависимостей и включить фичу постепенно через feature flag.
