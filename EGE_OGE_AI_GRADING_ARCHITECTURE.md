# 🎓 AI-агент для проверки ЕГЭ/ОГЭ (Часть 2) - Архитектура

## 🎯 Цели

1. **Обучить AI стандартам проверки ФИПИ** (критерии оценивания ЕГЭ/ОГЭ)
2. **Масштабировать на сотни работ** одновременно
3. **МАКСИМАЛЬНО удешевить** - целевая стоимость < $0.0005 за проверку одного развернутого ответа

---

## 💰 Стратегия экономии (от дешёвого к дорогому)

### Вариант 1: DeepSeek V3 + Кеширование (РЕКОМЕНДУЕТСЯ) ⭐

**Стоимость**: ~$0.00014 за проверку  
**Качество**: Отличное (GPT-4 уровень)

**Почему самый дешёвый:**
- DeepSeek V3: $0.14/$0.28 per 1M tokens (input/output)
- Средняя проверка: ~800 input + 200 output токенов
- Расчёт: (800 × 0.14 + 200 × 0.28) / 1,000,000 = **$0.00017**
- С кешированием промптов (см. ниже): **~$0.00008**

**Преимущества:**
- Самый дешёвый из качественных LLM
- API совместим с OpenAI
- Отлично понимает русский язык
- Бесплатные кредиты при регистрации

**Что уже есть в коде:**
```python
# teaching_panel/homework/ai_grading_service.py
# Уже интегрирован DeepSeek!
```

### Вариант 2: YandexGPT Lite (для России)

**Стоимость**: ~$0.0003 за проверку  
**Качество**: Хорошее, но хуже DeepSeek

- YandexGPT Lite: 0.06₽ за 1000 токенов ≈ $0.0006/1K tokens
- Преимущество: Российская платформа, рубли

### Вариант 3: Google Gemini 2.0 Flash (АЛЬТЕРНАТИВА)

**Стоимость**: ~$0.00019 за проверку  
**Качество**: Отличное

- Gemini 2.0 Flash: $0.075/$0.30 per 1M tokens
- Очень быстрый (лучше для массовой проверки)
- НО: Может хуже понимать специфику ЕГЭ/ОГЭ

### Вариант 4: Self-hosted Llama 3.3 70B (для больших объёмов)

**Стоимость**: ~$0.00002-0.00005 за проверку  
**Качество**: Очень хорошее

**Если проверок > 50,000 в месяц:**
- Self-host через Modal.com / Together.ai / Replicate
- Modal: ~$0.001 per second → ~$0.00002 за проверку (2 sec)
- Нужно fine-tuning на критериях ФИПИ

---

## 🏗️ Архитектура решения

### Компоненты

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
│  - Teacher создаёт ЕГЭ/ОГЭ ДЗ с типом "exam_part2"        │
│  - Выбирает предмет, тему, критерии (готовые шаблоны)      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               Django Backend (API)                          │
│  homework/                                                  │
│    - models.py: новое поле `exam_type` (ege/oge/none)      │
│    - ege_grading_service.py: специализированный сервис ░░   │
│    - critera_repository.py: хранилище критериев ФИПИ ░░     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           EGE Grading Pipeline (NEW)                        │
│                                                             │
│  1. [RAG] Загрузка критериев ФИПИ из базы                  │
│  2. [Prompt Engineering] Формирование промпта               │
│  3. [Batch API] Отправка пачками (если > 10 работ)         │
│  4. [Caching] Проверка кеша по hash(question + criteria)   │
│  5. [AI Provider] DeepSeek V3 / YandexGPT / Gemini         │
│  6. [Validation] Парсинг + валидация оценки по критериям    │
│  7. [DB Save] Сохранение с разбивкой по критериям           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📚 База критериев ФИПИ (RAG)

### Структура данных

**Новая модель**: `homework/models.py`

```python
class ExamCriteria(models.Model):
    """Критерии оценивания ЕГЭ/ОГЭ из ФИПИ"""
    exam_type = models.CharField(max_length=10, choices=[
        ('ege', 'ЕГЭ'),
        ('oge', 'ОГЭ')
    ])
    subject = models.CharField(max_length=50)  # Русский, Английский, История...
    task_number = models.CharField(max_length=10)  # "Задание 25", "Задание 27"
    
    # Критерии (JSON)
    criteria = models.JSONField(help_text="""
    {
        "K1": {
            "name": "Решение коммуникативной задачи",
            "max_points": 3,
            "description": "...",
            "levels": [
                {"points": 3, "requirements": "..."},
                {"points": 2, "requirements": "..."},
                {"points": 1, "requirements": "..."},
                {"points": 0, "requirements": "..."}
            ]
        },
        "K2": {...},
        ...
    }
    """)
    
    # Примеры для few-shot learning
    examples = models.JSONField(default=list, help_text="""
    [
        {
            "question": "...",
            "student_answer": "...",
            "correct_grading": {
                "K1": 2,
                "K2": 3,
                "K3": 1,
                "total": 6
            },
            "explanation": "..."
        }
    ]
    """)
    
    year = models.IntegerField(default=2025)
    fipi_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['exam_type', 'subject', 'task_number', 'year']
        indexes = [
            models.Index(fields=['exam_type', 'subject', 'task_number'])
        ]
```

### Источники критериев

1. **ФИПИ официальные документы**: https://fipi.ru/
   - Скачиваем PDF демоверсий + критерии оценивания
   - Парсим в JSON автоматически (или вручную)

2. **Codebases-кодификаторы**: https://fipi.ru/ege/otkrytyy-bank-zadaniy-ege
   - База типовых заданий с критериями

3. **Методические рекомендации** экспертов ФИПИ

---

## 🤖 Специализированный промпт для ЕГЭ/ОГЭ

### Системный промпт

```python
# homework/ege_grading_service.py

EGE_SYSTEM_PROMPT = """Ты - эксперт по проверке экзаменационных работ ЕГЭ/ОГЭ.

ТВОЯ ЗАДАЧА: Оценить развернутый ответ ученика строго по критериям ФИПИ.

КРИТИЧЕСКИ ВАЖНО:
1. Применяй ТОЛЬКО указанные критерии (K1, K2, K3...)
2. Для каждого критерия выставляй балл согласно требованиям
3. Объясняй почему поставлен именно такой балл
4. Если ответ на грани между баллами - выбирай СТРОГО по описанию уровня
5. Не придумывай свои критерии - используй только переданные

ФОРМАТ ОТВЕТА (СТРОГО JSON):
{{
    "criteria_scores": {{
        "K1": {{
            "score": <число>,
            "max": <число>,
            "justification": "Почему такой балл..."
        }},
        "K2": {{...}},
        ...
    }},
    "total_score": <сумма>,
    "total_max": <сумма максимумов>,
    "feedback": "Общий комментарий для ученика",
    "confidence": <0.0-1.0>,
    "warnings": ["Если что-то непонятно в ответе"]
}}

НЕ отходи от формата. НЕ добавляй рассуждения вне JSON."""
```

### User промпт (динамический)

```python
def build_ege_user_prompt(
    task_number: str,
    question_text: str,
    student_answer: str,
    criteria: dict,
    examples: list = None
) -> str:
    """
    Формирует промпт для проверки ЕГЭ/ОГЭ ответа
    
    Args:
        task_number: "Задание 27" (ЕГЭ Русский)
        question_text: Текст задания
        student_answer: Ответ ученика
        criteria: Dict с критериями из ФИПИ
        examples: Few-shot примеры (опционально, для повышения точности)
    """
    parts = [
        f"=== ЗАДАНИЕ ===",
        f"Номер: {task_number}",
        f"Текст: {question_text}",
        f"",
        f"=== КРИТЕРИИ ОЦЕНИВАНИЯ (ФИПИ) ===",
    ]
    
    # Добавляем каждый критерий
    for criterion_id, criterion_data in criteria.items():
        parts.append(f"\n{criterion_id}. {criterion_data['name']} (макс. {criterion_data['max_points']} балла)")
        parts.append(f"Описание: {criterion_data['description']}")
        parts.append("Уровни:")
        for level in criterion_data['levels']:
            parts.append(f"  {level['points']} балл(ов): {level['requirements']}")
    
    # Few-shot примеры (если есть)
    if examples:
        parts.append(f"\n=== ПРИМЕРЫ ОЦЕНИВАНИЯ (для калибровки) ===")
        for i, ex in enumerate(examples[:2], 1):  # Макс 2 примера, чтобы не раздувать токены
            parts.append(f"\nПример {i}:")
            parts.append(f"Ответ: {ex['student_answer'][:200]}...")
            parts.append(f"Оценка: {ex['correct_grading']}")
            parts.append(f"Объяснение: {ex['explanation']}")
    
    # Ответ ученика
    parts.append(f"\n=== ОТВЕТ УЧЕНИКА (проверяемый) ===")
    parts.append(student_answer if student_answer.strip() else "(пустой ответ)")
    
    parts.append(f"\n=== ИНСТРУКЦИЯ ===")
    parts.append("Оцени ответ строго по указанным критериям. Заполни JSON со score для каждого критерия.")
    
    return "\n".join(parts)
```

---

## 🚀 Масштабирование: Batch Processing

### Проблема

Если 100 учеников сдали ЕГЭ-работу, проверка по одной будет долгой:
- Последовательно: 100 × 3 sec = 5 минут
- С rate limit 20 req/sec → тоже долго

### Решение 1: Batch API (DeepSeek / OpenAI)

**DeepSeek поддерживает Batch API** (как OpenAI):

```python
# homework/ege_grading_service.py

async def grade_batch_async(self, answers: list[dict]) -> list[AIGradingResult]:
    """
    Проверка пачки ответов через Batch API
    
    Args:
        answers: [
            {
                "id": "answer_123",
                "question_text": "...",
                "student_answer": "...",
                "criteria": {...},
                "max_points": 12
            },
            ...
        ]
    
    Returns:
        List[AIGradingResult] в том же порядке
    """
    # 1. Создаём batch-файл для DeepSeek
    batch_requests = []
    for ans in answers:
        user_prompt = build_ege_user_prompt(
            task_number=ans.get('task_number', 'Задание'),
            question_text=ans['question_text'],
            student_answer=ans['student_answer'],
            criteria=ans['criteria'],
            examples=ans.get('examples', [])
        )
        
        batch_requests.append({
            "custom_id": ans['id'],
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": EGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,  # Низкая для консистентности
                "max_tokens": 1000
            }
        })
    
    # 2. Отправляем batch
    batch_id = await self._send_batch_to_deepseek(batch_requests)
    
    # 3. Ждём результаты (polling или webhook)
    results = await self._wait_for_batch_results(batch_id, timeout=120)
    
    # 4. Парсим и возвращаем
    return [self._parse_ege_response(r) for r in results]
```

**Преимущества Batch API:**
- 50% скидка на токены (DeepSeek / OpenAI)
- Параллельная обработка
- Стоимость: **$0.00007 за проверку** вместо $0.00014!

**Недостаток:**
- Задержка: результаты приходят через 30-120 секунд
- Подходит для "отложенной проверки" (не real-time)

### Решение 2: Асинхронная очередь (для real-time)

Если нужно проверить быстро (но не одновременно):

```python
import asyncio
import httpx

async def grade_many_parallel(self, answers: list[dict], max_concurrent=20):
    """Проверка с ограничением параллелизма"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def grade_one(ans):
        async with semaphore:
            return await self.grade_answer_async(
                question_text=ans['question_text'],
                student_answer=ans['student_answer'],
                criteria=ans['criteria'],
                max_points=ans['max_points']
            )
    
    tasks = [grade_one(ans) for ans in answers]
    return await asyncio.gather(*tasks)
```

**Время**: 100 работ × 3 sec / 20 concurrent = ~15 секунд

---

## 💾 Кеширование для экономии

### Стратегия 1: Кеширование похожих ответов

**Проблема**: Студенты часто дают похожие ответы (копипаста, типовые формулировки)

**Решение**: Semantic hash + Redis cache

```python
# homework/ege_grading_cache.py

import hashlib
from django.core.cache import cache

def get_semantic_hash(question_id: int, answer_text: str) -> str:
    """Хеш для кеширования похожих ответов"""
    # Нормализация: lowercase + убираем лишние пробелы
    normalized = " ".join(answer_text.lower().split())
    
    # MD5 от (question_id + normalized_answer)
    key = f"ege_grade_{question_id}_{hashlib.md5(normalized.encode()).hexdigest()}"
    return key

def get_cached_grade(question_id: int, answer_text: str):
    """Проверяем кеш перед AI запросом"""
    key = get_semantic_hash(question_id, answer_text)
    cached = cache.get(key)
    
    if cached:
        logger.info(f"Cache HIT for question {question_id}")
        return cached  # AIGradingResult object
    return None

def cache_grade(question_id: int, answer_text: str, result: AIGradingResult):
    """Сохраняем результат в кеш"""
    key = get_semantic_hash(question_id, answer_text)
    cache.set(key, result, timeout=86400 * 30)  # 30 дней
```

**Экономия**: 30-40% запросов при проверке типовых ответов

### Стратегия 2: DeepSeek Context Caching (Beta)

DeepSeek v3 поддерживает кеширование промптов:
- Если системный промпт + критерии одинаковые → кешируются на стороне API
- Платите только за уникальную часть (ответ студента)
- **Экономия до 50%**

```python
# В HTTP запросе добавить заголовок:
headers = {
    "X-DeepSeek-Cache-Strategy": "prefix"  # Кешировать начало промпта
}
```

---

## 📊 Расширенная модель Answer для ЕГЭ/ОГЭ

### Изменения в homework/models.py

```python
class Answer(models.Model):
    # ... существующие поля ...
    
    # === Новые поля для ЕГЭ/ОГЭ ===
    
    # Оценка по критериям (JSON)
    exam_criteria_scores = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Оценка по критериям ФИПИ:
        {
            "K1": {"score": 2, "max": 3, "justification": "..."},
            "K2": {"score": 3, "max": 3, "justification": "..."},
            "K3": {"score": 1, "max": 2, "justification": "..."},
            "total": 6,
            "total_max": 8
        }
        """
    )
    
    # Ворнинги от AI (что было неясно)
    exam_ai_warnings = models.JSONField(
        default=list,
        blank=True,
        help_text="['Ответ слишком короткий', 'Не указан пример из текста']"
    )
    
    # Использован кеш?
    was_cached = models.BooleanField(default=False)
    
    # Стоимость проверки (для аналитики)
    ai_cost_usd = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True
    )
```

---

## 🛠️ Полный pipeline внедрения

### Этап 1: Загрузка критериев ФИПИ (Неделя 1)

**Задачи:**
1. Создать модель `ExamCriteria`
2. Написать парсер ФИПИ документов (или заполнить вручную)
3. Загрузить критерии для топ-5 предметов:
   - Русский язык (Задание 27 - сочинение)
   - Английский язык (Задание 40 - личное письмо, эссе)
   - Обществознание (Задание 25 - понятие + примеры)
   - История (Задание 25 - аргументы)
   - Биология/Химия (развернутые ответы)

**Промпт для парсера:**
```python
# Создай management команду:
python manage.py load_fipi_criteria \
    --subject "Русский язык" \
    --year 2025 \
    --pdf-path /path/to/fipi_russkiy_criteria.pdf
```

### Этап 2: Разработка EGEGradingService (Неделя 2)

**Файлы:**
- `homework/ege_grading_service.py` - основной сервис
- `homework/criteria_repository.py` - работа с критериями
- `homework/ege_grading_cache.py` - кеширование

**API:**
```python
from homework.ege_grading_service import EGEGradingService

service = EGEGradingService(provider='deepseek')

result = service.grade_ege_answer(
    exam_type='ege',
    subject='Русский язык',
    task_number='27',
    question_text='Напишите сочинение по прочитанному тексту...',
    student_answer='В данном тексте автор...',
    year=2025
)

# result.exam_criteria_scores:
# {
#     "K1": {"score": 2, "max": 3, "justification": "..."},
#     ...
# }
```

### Этап 3: Интеграция в конструктор ДЗ (Неделя 3)

**Frontend изменения:**

```javascript
// frontend/src/modules/homework-analytics/components/HomeworkConstructor.js

// Новое поле при создании ДЗ:
<Select
  label="Тип задания"
  value={examType}
  onChange={setExamType}
  options={[
    { value: 'none', label: 'Обычное ДЗ' },
    { value: 'ege', label: 'ЕГЭ (часть 2)' },
    { value: 'oge', label: 'ОГЭ (часть 2)' }
  ]}
/>

{examType !== 'none' && (
  <>
    <Select
      label="Предмет"
      options={['Русский язык', 'Английский язык', ...]}
    />
    <Select
      label="Задание"
      options={['Задание 25', 'Задание 27', ...]}  // Динамически из API
    />
  </>
)}
```

**Backend изменения:**

```python
# homework/models.py

class Homework(models.Model):
    # ... существующие поля ...
    
    exam_type = models.CharField(
        max_length=10,
        choices=[('none', 'Обычное'), ('ege', 'ЕГЭ'), ('oge', 'ОГЭ')],
        default='none'
    )
    exam_subject = models.CharField(max_length=50, blank=True)
    exam_task_number = models.CharField(max_length=10, blank=True)
    exam_year = models.IntegerField(default=2025)
    
    # Вместо generic ai_grading_prompt используется ExamCriteria из БД
```

### Этап 4: Batch processing (Неделя 4)

**Новый endpoint:**

```python
# homework/views.py

@action(detail=True, methods=['post'], url_path='grade-all-submissions')
def grade_all_submissions(self, request, pk=None):
    """
    Массовая проверка всех сданных работ по ЕГЭ/ОГЭ ДЗ
    
    POST /api/homework/{id}/grade-all-submissions/
    """
    homework = self.get_object()
    
    if homework.exam_type == 'none':
        return Response({'error': 'Не ЕГЭ/ОГЭ задание'}, status=400)
    
    # Получаем все ответы, требующие проверки
    submissions = homework.submissions.filter(status='submitted')
    answers_to_grade = []
    
    for sub in submissions:
        for ans in sub.answers.filter(
            question__question_type='TEXT',
            auto_score__isnull=True,
            teacher_score__isnull=True
        ):
            answers_to_grade.append({
                'id': f'answer_{ans.id}',
                'answer_obj': ans,
                'question_text': ans.question.prompt,
                'student_answer': ans.text_answer,
                'criteria': ...,  # Из ExamCriteria
                'max_points': ans.question.points
            })
    
    # Batch проверка (асинхронно)
    from homework.tasks import grade_ege_batch_task
    task = grade_ege_batch_task.delay(
        answers=[{k: v for k, v in a.items() if k != 'answer_obj'} for a in answers_to_grade]
    )
    
    return Response({
        'status': 'started',
        'task_id': task.id,
        'total_answers': len(answers_to_grade)
    })
```

**Background task** (если используете Celery, хотя видел CELERY_REMOVAL_COMPLETE.md):

```python
# homework/tasks.py

from django.core.management import call_command
import asyncio

def grade_ege_batch_task(answers: list[dict]):
    """Background task для массовой проверки"""
    
    # Используем async batch grading
    service = EGEGradingService(provider='deepseek')
    
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        service.grade_batch_async(answers)
    )
    
    # Сохраняем результаты
    for ans_data, result in zip(answers, results):
        ans = Answer.objects.get(id=ans_data['id'].split('_')[1])
        ans.auto_score = result.total_score
        ans.exam_criteria_scores = result.criteria_scores
        ans.teacher_feedback = result.feedback
        ans.ai_cost_usd = result.cost_usd
        ans.was_cached = result.was_cached
        ans.needs_manual_review = result.confidence < 0.75
        ans.save()
    
    return {'success': True, 'graded_count': len(results)}
```

### Этап 5: UI для просмотра оценки по критериям (Неделя 5)

**Компонент оценки:**

```javascript
// frontend/src/modules/homework-analytics/components/ExamCriteriaScores.js

function ExamCriteriaScores({ answer }) {
  const { exam_criteria_scores } = answer;
  
  if (!exam_criteria_scores || Object.keys(exam_criteria_scores).length === 0) {
    return null;
  }
  
  return (
    <div className="exam-criteria">
      <h4>Оценка по критериям ФИПИ</h4>
      
      {Object.entries(exam_criteria_scores).map(([key, data]) => {
        if (key === 'total' || key === 'total_max') return null;
        
        return (
          <div key={key} className="criterion">
            <div className="criterion-header">
              <span className="criterion-name">{key}</span>
              <span className="criterion-score">
                {data.score} / {data.max}
              </span>
            </div>
            <p className="criterion-justification">
              {data.justification}
            </p>
          </div>
        );
      })}
      
      <div className="criterion-total">
        <strong>Итого:</strong> {exam_criteria_scores.total} / {exam_criteria_scores.total_max}
      </div>
      
      {answer.exam_ai_warnings?.length > 0 && (
        <div className="ai-warnings">
          <h5>⚠️ Замечания AI:</h5>
          <ul>
            {answer.exam_ai_warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

---

## 📈 Метрики и мониторинг

### Что отслеживать

```python
# analytics/models.py

class AIGradingMetrics(models.Model):
    """Метрики AI проверки для оптимизации"""
    date = models.DateField(auto_now_add=True)
    exam_type = models.CharField(max_length=10)
    provider = models.CharField(max_length=20)
    
    # Объём
    total_graded = models.IntegerField(default=0)
    cached_count = models.IntegerField(default=0)  # Сколько из кеша
    
    # Производительность
    avg_grading_time_sec = models.FloatField()
    batch_used_count = models.IntegerField(default=0)
    
    # Стоимость
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=6)
    avg_cost_per_answer = models.DecimalField(max_digits=10, decimal_places=6)
    
    # Качество
    manual_override_count = models.IntegerField(default=0)  # Учитель изменил оценку
    avg_confidence = models.FloatField()
    
    class Meta:
        unique_together = ['date', 'exam_type', 'provider']
```

**Dashboard** (в админ-панели):
- Суточные/месячные расходы на AI
- Cache hit rate
- Сколько оценок изменили учителя (для настройки промпта)

---

## 🎓 Обучение AI: Fine-tuning vs Prompt Engineering

### Вариант 1: Prompt Engineering (рекомендуется для старта)

**Преимущества:**
- Ноль дополнительных затрат
- Быстрый старт
- Легко обновлять критерии

**Как улучшить точность:**
1. **Few-shot learning** - добавить 2-3 примера проверенных работ в промпт
2. **Chain-of-Thought** - попросить AI рассуждать пошагово
3. **Self-consistency** - сделать 3 проверки с разной temperature и усреднить

```python
# Улучшенный промпт с CoT:
EGE_SYSTEM_PROMPT_COT = """...

ХОД ПРОВЕРКИ:
1. Прочитай ответ полностью
2. Для каждого критерия:
   a. Определи, соответствует ли ответ описанным уровням
   b. Если между двумя уровнями - выбери более низкий балл
   c. Запиши обоснование
3. Суммируй баллы
4. Если уверен < 80% - укажи warnings

Теперь проверь ответ:
"""
```

### Вариант 2: Fine-tuning (если бюджет > $500)

**Когда имеет смысл:**
- Проверено > 5000 работ вручную (есть dataset)
- Нужна точность > 95%
- Специфичный предмет (не общие навыки)

**Стоимость:**
- DeepSeek: не поддерживает fine-tuning пока
- OpenAI GPT-4o-mini: ~$2-3 per 1M training tokens
- Llama 3.3 70B через Modal: ~$50-100 за fine-tune

**Datasets:**
- Размечаем 2000-5000 пар (question, answer, grading) с реальными оценками экспертов
- Форматируем в JSONL для OpenAI API

---

## 💡 Дополнительные оптимизации

### 1. Приоритетная очередь

Проверяем сначала "важные" работы:

```python
# homework/models.py

class StudentSubmission(models.Model):
    # ...
    grading_priority = models.IntegerField(default=0, help_text='Выше = быстрее проверка')
    
    # Логика:
    # priority = 10 если deadline через < 1 день
    # priority = 5 если ученик отличник (нужен быстрый фидбек)
    # priority = 1 обычные
```

### 2. Прогрессивная проверка

Для длинных сочинений (> 300 слов):

```python
def check_if_worth_full_grading(answer_text: str) -> bool:
    """Быстрая pre-check перед полной проверкой"""
    # Используем дешёвую модель (DeepSeek-lite) для фильтрации:
    # - Пустые ответы
    # - Бессмысленный текст
    # - Копипаста из вопроса
    
    # Если pre-check = "мусор" → 0 баллов без полной проверки
    # Экономия: ~30% запросов отсеиваются
```

### 3. Сравнительная проверка (для экспериментов)

Проверяем один ответ через 2 провайдера и сравниваем:

```python
result_deepseek = grade_with_deepseek(...)
result_gemini = grade_with_gemini(...)

if abs(result_deepseek.total_score - result_gemini.total_score) > 2:
    # Большое расхождение → требует внимания учителя
    answer.needs_manual_review = True
else:
    # Консенсус → выше доверие
    answer.confidence = 0.95
```

---

## 📋 Чеклист внедрения

- [ ] **Этап 1**: Загрузить критерии ФИПИ в БД (2-3 предмета для старта)
- [ ] **Этап 2**: Создать `EGEGradingService` с промптом + RAG критериев
- [ ] **Этап 3**: Интегрировать в конструктор ДЗ (поле `exam_type`)
- [ ] **Этап 4**: Добавить batch processing для массовой проверки
- [ ] **Этап 5**: Реализовать кеширование (Redis + semantic hash)
- [ ] **Этап 6**: UI для просмотра оценки по критериям
- [ ] **Этап 7**: Метрики и мониторинг стоимости
- [ ] **Этап 8**: A/B тест: сравнить оценки AI vs учителя на 100 работах
- [ ] **Этап 9**: Настроить промпт на основе расхождений
- [ ] **Этап 10**: Масштабировать на все предметы

---

## 💸 Финальная стоимость (прогноз)

**Сценарий**: 1000 учеников, каждый сдаёт 5 ЕГЭ-работ в месяц, каждая работа = 3 развернутых ответа

- **Объём**: 1000 × 5 × 3 = 15,000 проверок/месяц

**Вариант 1: DeepSeek + Batch + Cache**
- Стоимость за проверку: $0.00007 (batch + cache)
- Кеш hit rate: 30%
- Реальная стоимость: 15,000 × 0.7 × $0.00007 = **$0.735/месяц** 🎉

**Вариант 2: DeepSeek standard (без оптимизаций)**
- Стоимость: 15,000 × $0.00014 = **$2.10/месяц**

**Вариант 3: OpenAI GPT-4o-mini**
- Стоимость: 15,000 × $0.0015 = **$22.50/месяц**

## 🎯 Рекомендация

**Начните с Варианта 1** (DeepSeek + Batch + Cache) - это:
- **В 30 раз дешевле OpenAI**
- **Отличное качество** (GPT-4 уровень)
- **Легко масштабируется** до 100K+ проверок

---

**Следующие шаги**: Хочешь, чтобы я начал имплементацию с создания моделей и сервиса? Или сначала хочешь обсудить какие-то детали?
