# Интеграция AI-проверки ЕГЭ/ОГЭ - Практическое руководство

## 📋 Содержание
1. [Обзор решения](#обзор-решения)
2. [Экономика проекта](#экономика-проекта)
3. [Архитектура](#архитектура)
4. [Пошаговая интеграция](#пошаговая-интеграция)
5. [Примеры использования](#примеры-использования)
6. [Обучение AI стандартам ФИПИ](#обучение-ai-стандартам-фипи)
7. [Масштабирование](#масштабирование)

---

## 🎯 Обзор решения

### Что мы делаем
Интегрируем специализированный AI-агент для проверки развернутых ответов ЕГЭ/ОГЭ (второй части экзаменов) с **фокусом на максимальную экономию** и соответствие стандартам ФИПИ.

### Ключевые особенности
- ✅ **Детальная проверка по критериям ФИПИ** (K1-K12 для ЕГЭ Русский, и т.д.)
- ✅ **Супер-дешево**: ~0.015-0.03₽ за работу (в 100+ раз дешевле GPT-4)
- ✅ **Пакетная обработка**: класс из 30 учеников = ~0.45-0.90₽
- ✅ **Кэширование**: повторная проверка = 0₽
- ✅ **Примеры ошибок** с указанием фрагментов текста
- ✅ **Интеграция** в существующую систему homework без переписывания

---

## 💰 Экономика проекта

### Сравнение стоимости моделей (для сочинения ~2000 символов)

| Модель | Стоимость/работа | Стоимость/30 работ | Качество |
|--------|------------------|---------------------|----------|
| **DeepSeek Chat** 🥇 | **0.015₽** | **0.45₽** | Отлично |
| DeepSeek Reasoner | 0.06₽ | 1.80₽ | Великолепно |
| Mistral Small | 0.11₽ | 3.30₽ | Отлично |
| GPT-4o-mini | 0.21₽ | 6.30₽ | Хорошо |
| GPT-4o | 3.50₽ | 105₽ | Избыточно |

**Рекомендация**: Используем **DeepSeek Chat** как основную модель (оптимальное соотношение цена/качество).

### Реальные цифры для школы

**Сценарий 1: Класс из 30 учеников пишет сочинение ЕГЭ**
```
Модель: DeepSeek Chat
Средняя длина: 2000 символов
Стоимость: 30 × 0.015₽ = 0.45₽

Время учителя без AI: 30 × 15 мин = 7.5 часов
Время учителя с AI: 30 × 3 мин = 1.5 часов (только финальная проверка)
Экономия времени: 6 часов (80%)
```

**Сценарий 2: Подготовка к ЕГЭ, 3 пробных сочинения**
```
Учеников: 30
Пробных работ: 3
Работ всего: 90

Стоимость: 90 × 0.015₽ = 1.35₽
Экономия времени: 18 часов работы учителя
```

**Сценарий 3: Репетитор с 10 учениками в месяц**
```
Учеников: 10
Работ в месяц: 40 (по 4 работы на ученика)
Стоимость: 40 × 0.015₽ = 0.60₽/месяц
Стоимость в год: 7.20₽

Экономия времени: ~10 часов/месяц = 120 часов/год
```

### Оптимизация затрат

**1. Кэширование (бесплатная повторная проверка)**
```python
# Первая проверка: 0.015₽
result = grade_ege_essay(source, answer, use_cache=True)

# Повторная проверка того же ответа: 0₽ (из кэша)
result = grade_ege_essay(source, answer, use_cache=True)
```

**2. Сжатые промпты (-40% токенов)**
```python
# Полный промпт: ~1000 токенов
build_prompt(..., optimized=False)

# Сжатый промпт: ~600 токенов (используется по умолчанию)
build_prompt(..., optimized=True)
```

**3. Batch-проверка (-20% за счет переиспользования контекста)**
```python
# Проверяем весь класс одним запросом
results = service.grade_batch_sync(works, batch_size=30)
```

---

## 🏗️ Архитектура

### Компоненты системы

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
│  - Отображение детальных оценок по критериям               │
│  - Показ примеров ошибок с подсветкой                      │
│  - UI для включения/отключения AI проверки                 │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP API
┌──────────────────────▼──────────────────────────────────────┐
│               Django Backend (homework app)                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ HomeworkSubmissionViewSet (views.py)                  │ │
│  │  - Endpoint для проверки AI: /check-with-ai/          │ │
│  │  - Автопроверка при сдаче (если включена)             │ │
│  └───────────┬───────────────────────────────────────────┘ │
│              │                                               │
│  ┌───────────▼───────────────────────────────────────────┐ │
│  │ ExamAIGradingService (exam_ai_grading_service.py)    │ │
│  │  - Основная логика проверки ЕГЭ/ОГЭ                  │ │
│  │  - Работа с критериями ФИПИ                           │ │
│  │  - Кэширование результатов                            │ │
│  └───────────┬───────────────────────────────────────────┘ │
│              │                                               │
│  ┌───────────▼───────────────────────────────────────────┐ │
│  │ AI Grading Examples (ai_grading_examples.py)         │ │
│  │  - Критерии ФИПИ (EGE_CRITERIA, OGE_CRITERIA)        │ │
│  │  - Промпты для разных типов заданий                  │ │
│  │  - Примеры правильных/неправильных ответов           │ │
│  └───────────┬───────────────────────────────────────────┘ │
│              │                                               │
│  ┌───────────▼───────────────────────────────────────────┐ │
│  │ Base AIGradingService (ai_grading_service.py)        │ │
│  │  - HTTP клиент для DeepSeek API                      │ │
│  │  - Базовые методы вызова AI                          │ │
│  └───────────┬───────────────────────────────────────────┘ │
└──────────────┼───────────────────────────────────────────────┘
               │ HTTPS API
┌──────────────▼───────────────────────────────────────────────┐
│                    DeepSeek API                              │
│  - deepseek-chat (основная модель)                          │
│  - deepseek-reasoner (для сложных случаев)                  │
└──────────────────────────────────────────────────────────────┘
```

### База данных (расширение существующих моделей)

```python
# homework/models.py

class Question(models.Model):
    # Существующие поля...
    
    # НОВЫЕ ПОЛЯ для ЕГЭ/ОГЭ
    exam_type = models.CharField(
        max_length=10,
        choices=[('EGE', 'ЕГЭ'), ('OGE', 'ОГЭ'), ('NONE', 'Обычное')],
        default='NONE'
    )
    exam_task_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Код задания: russian_27, math_profile_19, social_29, etc."
    )
    enable_ai_grading = models.BooleanField(
        default=False,
        help_text="Включить автоматическую AI проверку"
    )


class Answer(models.Model):
    # Существующие поля...
    
    # НОВЫЕ ПОЛЯ для AI проверки
    ai_checked = models.BooleanField(default=False)
    ai_total_score = models.IntegerField(null=True, blank=True)
    ai_criteria_scores = models.JSONField(
        null=True, blank=True,
        help_text="Детальные оценки: {K1: {score: 1, reasoning: ...}, ...}"
    )
    ai_feedback = models.TextField(blank=True)
    ai_errors_found = models.JSONField(
        null=True, blank=True,
        help_text="Примеры ошибок: [{type, fragment, correction}, ...]"
    )
    ai_cost_rubles = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True
    )
    
    # Финальная оценка учителя (может отличаться от AI)
    teacher_override = models.BooleanField(default=False)
    teacher_notes = models.TextField(
        blank=True,
        help_text="Почему учитель изменил оценку AI"
    )
```

---

## 🔧 Пошаговая интеграция

### Шаг 1: Миграции БД

```bash
# Создаем миграцию для новых полей
cd teaching_panel
python manage.py makemigrations homework --name add_ai_grading_fields

# Применяем
python manage.py migrate homework
```

### Шаг 2: Добавляем API endpoint для AI проверки

```python
# homework/views.py

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from .exam_ai_grading_service import ExamAIGradingService, grade_ege_essay
from .ai_grading_examples import EGE_CRITERIA, OGE_CRITERIA


class HomeworkSubmissionViewSet(viewsets.ModelViewSet):
    # Существующий код...
    
    @action(detail=True, methods=['post'], url_path='check-with-ai')
    def check_with_ai(self, request, pk=None):
        """
        Проверяет ответ с помощью AI
        
        POST /api/homework/submissions/{id}/check-with-ai/
        
        Request body: {} (пустой, берем данные из submission)
        
        Response: {
            "success": true,
            "total_score": 16,
            "max_score": 25,
            "criteria_scores": {"K1": {"score": 1, "reasoning": "..."}, ...},
            "summary": "...",
            "strengths": ["..."],
            "weaknesses": ["..."],
            "examples_of_errors": [{"type": "...", "fragment": "...", "correction": "..."}],
            "cost_rubles": "0.0152",
            "model_used": "deepseek-chat"
        }
        """
        submission = self.get_object()  # Answer instance
        question = submission.question
        
        # Проверяем, что это вопрос с включенной AI проверкой
        if not question.enable_ai_grading:
            return Response(
                {"error": "AI проверка не включена для этого вопроса"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if question.exam_type not in ['EGE', 'OGE']:
            return Response(
                {"error": "AI проверка доступна только для ЕГЭ/ОГЭ заданий"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not question.exam_task_code:
            return Response(
                {"error": "Не указан код задания (exam_task_code)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем исходный текст задания и ответ студента
        source_text = question.question_text  # предполагаем, что тут исходный текст
        student_answer = submission.answer_text
        
        if not student_answer or not student_answer.strip():
            return Response(
                {"error": "Ответ студента пустой"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Вызываем AI проверку
            service = ExamAIGradingService(provider='deepseek', model='deepseek-chat')
            
            result = service.grade_exam_work_sync(
                source_text=source_text,
                student_answer=student_answer,
                criteria_key=question.exam_task_code,
                exam_type='ЕГЭ' if question.exam_type == 'EGE' else 'ОГЭ',
                subject=question.homework.subject or 'Русский язык',
                use_cache=True
            )
            
            # Сохраняем результат AI в БД
            submission.ai_checked = True
            submission.ai_total_score = result.total_score
            submission.ai_criteria_scores = result.criteria_scores
            submission.ai_feedback = result.summary
            submission.ai_errors_found = result.examples_of_errors
            submission.ai_cost_rubles = result.cost_rubles
            
            # Если учитель еще не проверял - ставим AI оценку как предварительную
            if submission.status == 'submitted':
                submission.status = 'ai_checked'
                submission.score = result.total_score  # предварительная оценка
            
            submission.save()
            
            # Возвращаем результат
            return Response({
                "success": True,
                "total_score": result.total_score,
                "max_score": result.max_score,
                "criteria_scores": result.criteria_scores,
                "summary": result.summary,
                "strengths": result.strengths,
                "weaknesses": result.weaknesses,
                "examples_of_errors": result.examples_of_errors,
                "cost_rubles": str(result.cost_rubles),
                "model_used": result.model_used,
                "tokens_used": result.tokens_used
            })
            
        except Exception as e:
            logger.exception(f"AI grading failed for submission {pk}")
            return Response(
                {"error": f"Ошибка AI проверки: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='batch-check-ai')
    def batch_check_ai(self, request):
        """
        Пакетная проверка нескольких ответов
        
        POST /api/homework/submissions/batch-check-ai/
        Body: {
            "submission_ids": [1, 2, 3, ...]
        }
        
        Response: {
            "success": true,
            "results": [
                {"id": 1, "success": true, "total_score": 16, ...},
                {"id": 2, "success": false, "error": "..."},
                ...
            ],
            "total_cost_rubles": "0.45"
        }
        """
        submission_ids = request.data.get('submission_ids', [])
        
        if not submission_ids:
            return Response(
                {"error": "Не указаны submission_ids"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        total_cost = Decimal(0)
        
        for sub_id in submission_ids:
            try:
                # Вызываем check_with_ai для каждого submission
                response = self.check_with_ai(request, pk=sub_id)
                
                if response.status_code == 200:
                    data = response.data
                    results.append({
                        "id": sub_id,
                        "success": True,
                        "total_score": data["total_score"],
                        "summary": data["summary"]
                    })
                    total_cost += Decimal(data["cost_rubles"])
                else:
                    results.append({
                        "id": sub_id,
                        "success": False,
                        "error": response.data.get("error", "Unknown error")
                    })
            except Exception as e:
                results.append({
                    "id": sub_id,
                    "success": False,
                    "error": str(e)
                })
        
        return Response({
            "success": True,
            "results": results,
            "total_checked": len([r for r in results if r["success"]]),
            "total_failed": len([r for r in results if not r["success"]]),
            "total_cost_rubles": str(total_cost)
        })
```

### Шаг 3: Обновляем serializers

```python
# homework/serializers.py

class AnswerSerializer(serializers.ModelSerializer):
    # Добавляем поля AI проверки
    ai_result = serializers.SerializerMethodField()
    
    class Meta:
        model = Answer
        fields = [
            # существующие поля...
            'ai_checked',
            'ai_total_score',
            'ai_result',  # сводка AI проверки
        ]
    
    def get_ai_result(self, obj):
        """Возвращает результат AI проверки в удобном формате"""
        if not obj.ai_checked:
            return None
        
        return {
            "checked": True,
            "total_score": obj.ai_total_score,
            "criteria_scores": obj.ai_criteria_scores,
            "feedback": obj.ai_feedback,
            "errors": obj.ai_errors_found,
            "cost": str(obj.ai_cost_rubles) if obj.ai_cost_rubles else None
        }


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            # существующие поля...
            'exam_type',
            'exam_task_code',
            'enable_ai_grading',
        ]
```

### Шаг 4: Frontend компонент для отображения AI проверки

```jsx
// frontend/src/modules/homework-analytics/components/AIGradingResult.jsx

import React from 'react';
import { Card, Badge } from '../../../shared/components';

export const AIGradingResult = ({ aiResult }) => {
  if (!aiResult || !aiResult.checked) {
    return null;
  }

  const { total_score, criteria_scores, feedback, errors } = aiResult;

  return (
    <Card className="ai-grading-result">
      <div className="header">
        <h3>Проверка AI</h3>
        <Badge variant="info">
          {total_score} баллов
        </Badge>
      </div>

      <div className="summary">
        <p>{feedback}</p>
      </div>

      {criteria_scores && (
        <div className="criteria-breakdown">
          <h4>Оценка по критериям</h4>
          {Object.entries(criteria_scores).map(([key, data]) => (
            <div key={key} className="criterion">
              <div className="criterion-header">
                <span className="criterion-name">{key}</span>
                <Badge variant={data.score > 0 ? "success" : "warning"}>
                  {data.score} б.
                </Badge>
              </div>
              <p className="criterion-reasoning">{data.reasoning}</p>
            </div>
          ))}
        </div>
      )}

      {errors && errors.length > 0 && (
        <div className="errors-found">
          <h4>Найденные ошибки</h4>
          {errors.map((err, idx) => (
            <div key={idx} className="error-item">
              <Badge variant="danger">{err.type}</Badge>
              <div className="error-details">
                <p className="fragment">"{err.fragment}"</p>
                {err.correction && (
                  <p className="correction">
                    → <strong>{err.correction}</strong>
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};
```

### Шаг 5: Кнопка "Проверить с AI" в интерфейсе учителя

```jsx
// frontend/src/modules/homework-analytics/components/TeacherSubmissionReview.jsx

import { useState } from 'react';
import { apiClient } from '../../../apiService';
import { Button } from '../../../shared/components';
import { AIGradingResult } from './AIGradingResult';

export const TeacherSubmissionReview = ({ submission }) => {
  const [aiResult, setAiResult] = useState(submission.ai_result);
  const [loading, setLoading] = useState(false);

  const handleCheckWithAI = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post(
        `/homework/submissions/${submission.id}/check-with-ai/`
      );
      setAiResult(response.data);
    } catch (error) {
      console.error('AI check failed:', error);
      alert('Ошибка AI проверки: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="submission-review">
      {/* Существующий интерфейс */}
      
      <div className="ai-section">
        {!aiResult && (
          <Button
            onClick={handleCheckWithAI}
            loading={loading}
            variant="secondary"
          >
            Проверить с AI
          </Button>
        )}
        
        <AIGradingResult aiResult={aiResult} />
      </div>
    </div>
  );
};
```

---

## 📚 Обучение AI стандартам ФИПИ

### Стратегия 1: Промпт-инжиниринг (уже реализовано)

AI "обучается" через детальный промпт с критериями ФИПИ:

```python
# ai_grading_examples.py уже содержит:

EGE_CRITERIA = {
    "russian_27": {
        "name": "ЕГЭ Русский язык - Задание 27 (сочинение)",
        "max_score": 25,
        "criteria": {
            "K1": {
                "name": "Формулировка проблемы",
                "max": 1,
                "levels": [...]
            },
            "K2": {
                "name": "Комментарий к проблеме",
                "max": 6,
                "levels": [...]
            },
            # ... все 12 критериев
        }
    }
}
```

AI получает эти критерии в каждом запросе и строго следует им.

### Стратегия 2: Few-shot примеры (опционально, для улучшения)

Добавляем примеры правильной проверки в промпт:

```python
# В ai_grading_examples.py уже есть EXAMPLE_1_STUDENT_ANSWER
# и EXAMPLE_1_EXPECTED_OUTPUT

# Можно добавить в промпт:
FEW_SHOT_EXAMPLES = """
ПРИМЕР ПРОВЕРКИ:

Исходный текст: [...]
Ответ ученика: "Автор поднимает проблему о сущности чести..."

Правильная оценка:
K1: 1 балл (проблема сформулирована верно)
K2: 2 балла (2 примера без пояснений и связи)
K3: 1 балл (позиция автора сформулирована)
...

Теперь проверь следующую работу:
"""
```

### Стратегия 3: Калибровка на реальных данных

```python
# Скрипт для калибровки AI на уже проверенных учителем работах

def calibrate_ai_on_teacher_data():
    """
    Берем 100 работ, проверенных учителем, прогоняем через AI,
    сравниваем результаты, корректируем промпты
    """
    from homework.models import Answer
    
    # Берем работы с финальными оценками учителя
    checked_answers = Answer.objects.filter(
        teacher_checked=True,
        question__exam_type='EGE'
    )[:100]
    
    discrepancies = []
    
    for answer in checked_answers:
        # Проверяем AI
        ai_result = grade_ege_essay(
            source_text=answer.question.question_text,
            student_answer=answer.answer_text
        )
        
        # Сравниваем с оценкой учителя
        teacher_score = answer.teacher_score
        ai_score = ai_result.total_score
        
        difference = abs(teacher_score - ai_score)
        
        if difference > 2:  # расхождение больше 2 баллов
            discrepancies.append({
                "answer_id": answer.id,
                "teacher_score": teacher_score,
                "ai_score": ai_score,
                "difference": difference,
                "text": answer.answer_text[:500]
            })
    
    # Выводим статистику
    print(f"Проверено работ: {len(checked_answers)}")
    print(f"Расхождений >2 баллов: {len(discrepancies)}")
    print(f"Средняя точность: {(1 - len(discrepancies)/len(checked_answers)) * 100:.1f}%")
    
    # Анализируем расхождения и корректируем промпты
    return discrepancies
```

---

## 📈 Масштабирование

### Для небольшой школы (100-200 учеников)

**Стратегия**: Синхронные запросы + кэширование
```python
# Достаточно текущей реализации
service = ExamAIGradingService()
result = service.grade_exam_work_sync(...)
```

**Затраты**: ~2-4₽ в месяц (30-40 сочинений)

### Для крупной школы (500+ учеников)

**Стратегия**: Batch processing + очереди

```python
# Используем Celery для фоновой проверки
from celery import shared_task

@shared_task
def check_submissions_batch(submission_ids):
    """Проверяет пакет работ в фоне"""
    service = ExamAIGradingService()
    
    works = []
    for sub_id in submission_ids:
        submission = Answer.objects.get(id=sub_id)
        works.append((
            submission.question.question_text,
            submission.answer_text,
            submission.question.exam_task_code
        ))
    
    # Batch проверка
    results = service.grade_batch_sync(works, batch_size=50)
    
    # Сохраняем результаты
    for sub_id, result in zip(submission_ids, results):
        if result:
            submission = Answer.objects.get(id=sub_id)
            submission.ai_checked = True
            submission.ai_total_score = result.total_score
            # ... остальные поля
            submission.save()
```

**Затраты**: ~10-20₽ в месяц (200-400 сочинений)

### Для образовательной платформы (1000+ учеников)

**Стратегия**: Асинхронные запросы + rate limiting + приоритизация

```python
import asyncio
from asyncio import Semaphore

class ScalableExamGradingService(ExamAIGradingService):
    def __init__(self, max_concurrent=10):
        super().__init__()
        self.semaphore = Semaphore(max_concurrent)
    
    async def grade_with_rate_limit(self, *args, **kwargs):
        async with self.semaphore:
            return await self.grade_exam_work_async(*args, **kwargs)
    
    async def grade_large_batch(self, works, priority_ids=None):
        """
        Проверяет большой пакет с приоритизацией
        
        Args:
            works: список работ
            priority_ids: ID работ с высоким приоритетом (проверяются первыми)
        """
        # Сортируем: сначала приоритетные
        if priority_ids:
            works_sorted = sorted(works, key=lambda w: w[3] in priority_ids, reverse=True)
        else:
            works_sorted = works
        
        # Запускаем с rate limiting
        tasks = [
            self.grade_with_rate_limit(...)
            for work in works_sorted
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
```

**Затраты**: ~50-100₽ в месяц (1000-2000 сочинений)

---

## 🧪 Тестирование и проверка качества

### Тест 1: Проверка стандартного примера

```bash
cd teaching_panel
python -c "
from homework.exam_ai_grading_service import grade_ege_essay
from homework.ai_grading_examples import EXAMPLE_1_SOURCE, EXAMPLE_1_STUDENT_ANSWER

result = grade_ege_essay(EXAMPLE_1_SOURCE, EXAMPLE_1_STUDENT_ANSWER)
print(f'Оценка: {result.total_score} / {result.max_score}')
print(f'Стоимость: {result.cost_rubles}₽')
print(result.summary)
"
```

### Тест 2: Сравнение с оценкой учителя

```python
# Скрипт: test_ai_accuracy.py

from homework.models import Answer
from homework.exam_ai_grading_service import grade_ege_essay

def test_ai_accuracy():
    # Берем 20 работ, проверенных учителем
    checked = Answer.objects.filter(
        teacher_checked=True,
        question__exam_task_code='russian_27'
    )[:20]
    
    matches = 0
    
    for answer in checked:
        result = grade_ege_essay(
            source_text=answer.question.question_text,
            student_answer=answer.answer_text
        )
        
        # Считаем match если расхождение ≤ 2 балла
        if abs(result.total_score - answer.teacher_score) <= 2:
            matches += 1
    
    accuracy = (matches / len(checked)) * 100
    print(f"Точность AI: {accuracy:.1f}% (± 2 балла)")
    
    return accuracy

if __name__ == "__main__":
    test_ai_accuracy()
```

---

## 🎓 Итого: Что получаем

1. **Экономия времени учителя**: 70-80% (с 15 минут до 3 минут на работу)
2. **Супер-низкая стоимость**: 0.015₽ за сочинение (класс = 0.45₽)
3. **Детальная обратная связь**: Оценка по всем критериям ФИПИ + примеры ошибок
4. **Масштабируемость**: От 10 до 10000+ учеников без изменения архитектуры
5. **Прозрачность**: Учитель всегда может переопределить оценку AI

**Рекомендуемый workflow**:
1. Ученик сдает работу → автоматическая AI проверка
2. Учитель видит предварительную оценку AI + детальный разбор
3. Учитель тратит 3 минуты на финальную корректировку (вместо 15 минут на полную проверку)
4. Итоговая оценка = AI + коррекция учителя

**Next steps**:
1. Применить миграции БД (Шаг 1)
2. Добавить API endpoints (Шаг 2)
3. Протестировать на 10 работах
4. Раскатить на production
5. Собрать обратную связь от учителей
6. Откалибровать промпты при необходимости
