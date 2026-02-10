"""
Специализированный AI-сервис для проверки ЕГЭ/ОГЭ работ

Расширяет базовый AIGradingService для работы со стандартами ФИПИ
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal

from django.core.cache import cache
import httpx

from .ai_grading_service import AIGradingService, AIGradingResult
from .ai_grading_examples import EGE_CRITERIA, OGE_CRITERIA, build_prompt

logger = logging.getLogger(__name__)


@dataclass
class ExamGradingResult:
    """Расширенный результат проверки ЕГЭ/ОГЭ работы"""
    # Базовые поля
    total_score: int
    max_score: int
    
    # Детализированные оценки по критериям
    criteria_scores: Dict[str, Dict[str, any]]  # {"K1": {"score": 1, "reasoning": "..."}}
    
    # Фидбек
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    examples_of_errors: List[Dict[str, str]]
    
    # Метаданные
    cost_rubles: Decimal
    model_used: str
    tokens_used: int
    exam_type: str  # "ЕГЭ" или "ОГЭ"
    subject: str  # "Русский язык", "Математика"
    task_name: str  # "Задание 27 (сочинение)"


class ExamAIGradingService:
    """
    Специализированный сервис для проверки ЕГЭ/ОГЭ работ
    
    Особенности:
    - Работа со стандартами ФИПИ
    - Детальная оценка по критериям
    - Примеры ошибок с указанием фрагментов
    - Кэширование результатов
    - Экономичное использование токенов
    """
    
    # Цены за 1M токенов (в рублях, курс 95₽/$)
    MODEL_COSTS = {
        "deepseek-chat": {"input": 1.33, "output": 2.66},  # $0.014/$0.028
        "deepseek-reasoner": {"input": 5.32, "output": 19.95},
        "gpt-4o-mini": {"input": 14.25, "output": 57.0},
    }
    
    def __init__(self, provider: str = 'deepseek', model: str = 'deepseek-chat'):
        """
        Args:
            provider: 'deepseek' или 'openai'
            model: модель для использования (рекомендуется deepseek-chat для экономии)
        """
        self.base_service = AIGradingService(provider=provider)
        self.model = model
        self.provider = provider
    
    def _get_cache_key(self, source_text: str, student_answer: str, criteria_key: str) -> str:
        """Генерирует ключ кэша для работы"""
        import hashlib
        content = f"{source_text}||{student_answer}||{criteria_key}"
        return f"exam_ai_grading:{hashlib.md5(content.encode()).hexdigest()}"
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        """Рассчитывает стоимость запроса в рублях"""
        costs = self.MODEL_COSTS.get(self.model, self.MODEL_COSTS["deepseek-chat"])
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return Decimal(str(round(input_cost + output_cost, 4)))
    
    def grade_exam_work_sync(
        self,
        source_text: str,
        student_answer: str,
        criteria_key: str,  # "russian_27", "math_profile_19", "social_29"
        exam_type: str = "ЕГЭ",
        subject: str = "Русский язык",
        use_cache: bool = True
    ) -> ExamGradingResult:
        """
        Проверяет экзаменационную работу (синхронно, для Django views)
        
        Args:
            source_text: исходный текст задания
            student_answer: ответ ученика
            criteria_key: ключ критериев из EGE_CRITERIA/OGE_CRITERIA
            exam_type: "ЕГЭ" или "ОГЭ"
            subject: название предмета
            use_cache: использовать кэш результатов
        
        Returns:
            ExamGradingResult с детальной оценкой
        """
        # Проверяем кэш
        cache_key = self._get_cache_key(source_text, student_answer, criteria_key)
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for {cache_key}")
                return ExamGradingResult(**cached)
        
        # Получаем критерии
        criteria_dict = EGE_CRITERIA if exam_type == "ЕГЭ" else OGE_CRITERIA
        if criteria_key not in criteria_dict:
            raise ValueError(f"Критерии '{criteria_key}' не найдены для {exam_type}")
        
        criteria = criteria_dict[criteria_key]
        
        # Строим оптимизированный промпт
        system_prompt, user_prompt = build_prompt(
            exam_type=exam_type,
            subject=subject,
            task_name=criteria["name"],
            criteria=criteria,
            source_text=source_text,
            student_answer=student_answer,
            optimized=True  # сжатый промпт для экономии
        )
        
        # Вызываем API
        try:
            result_json, input_tokens, output_tokens = self._call_api_sync(
                system_prompt,
                user_prompt
            )
            
            # Парсим результат
            result_data = self._parse_json_response(result_json)
            
            # Рассчитываем стоимость
            cost = self._calculate_cost(input_tokens, output_tokens)
            
            # Формируем результат
            grading_result = ExamGradingResult(
                total_score=result_data.get("total_score", 0),
                max_score=criteria.get("max_score", 0),
                criteria_scores=result_data.get("scores", {}),
                summary=result_data.get("summary", ""),
                strengths=result_data.get("strengths", []),
                weaknesses=result_data.get("weaknesses", []),
                examples_of_errors=result_data.get("examples_of_errors", []),
                cost_rubles=cost,
                model_used=self.model,
                tokens_used=input_tokens + output_tokens,
                exam_type=exam_type,
                subject=subject,
                task_name=criteria["name"]
            )
            
            # Кэшируем на 7 дней
            if use_cache:
                cache.set(cache_key, asdict(grading_result), timeout=60*60*24*7)
                logger.info(f"Cached result for {cache_key}")
            
            return grading_result
            
        except Exception as e:
            logger.exception(f"Exam grading error: {e}")
            # Возвращаем результат с ошибкой
            return ExamGradingResult(
                total_score=0,
                max_score=criteria.get("max_score", 0),
                criteria_scores={},
                summary=f"Ошибка AI проверки: {str(e)}. Требуется ручная проверка.",
                strengths=[],
                weaknesses=["AI проверка не удалась"],
                examples_of_errors=[],
                cost_rubles=Decimal(0),
                model_used=self.model,
                tokens_used=0,
                exam_type=exam_type,
                subject=subject,
                task_name=criteria["name"]
            )
    
    def _call_api_sync(self, system_prompt: str, user_prompt: str) -> Tuple[str, int, int]:
        """Синхронный вызов AI API"""
        api_url, api_key, _ = self.base_service._get_api_config()
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,  # низкая для стабильности
                    "response_format": {"type": "json_object"}  # форсируем JSON
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            
            return (
                content,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0)
            )
    
    def _parse_json_response(self, json_text: str) -> dict:
        """Парсит JSON ответ от AI"""
        try:
            # Убираем markdown обертки если есть
            if '```json' in json_text:
                json_text = json_text.split('```json')[1].split('```')[0]
            elif '```' in json_text:
                json_text = json_text.split('```')[1].split('```')[0]
            
            return json.loads(json_text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON: {json_text[:200]}...")
            raise ValueError(f"AI вернул невалидный JSON: {e}")
    
    def estimate_cost(
        self,
        num_works: int,
        avg_work_length: int = 2000,
        criteria_key: str = "russian_27"
    ) -> Dict[str, any]:
        """
        Оценивает стоимость проверки пакета работ
        
        Args:
            num_works: количество работ
            avg_work_length: средняя длина работы в символах
            criteria_key: тип задания для оценки
        
        Returns:
            dict: информация о стоимости
        """
        # Грубая оценка токенов
        # Системный промпт (оптимизированный): ~400 токенов
        # Исходный текст: ~500 символов = ~150 токенов
        # Ответ ученика: avg_work_length / 3 токенов
        # Ответ AI: ~800 токенов (детальный разбор)
        
        input_tokens_per_work = 400 + 150 + (avg_work_length // 3)
        output_tokens_per_work = 800
        
        total_input = input_tokens_per_work * num_works
        total_output = output_tokens_per_work * num_works
        
        total_cost = self._calculate_cost(total_input, total_output)
        cost_per_work = total_cost / num_works if num_works > 0 else Decimal(0)
        
        return {
            "num_works": num_works,
            "total_cost_rubles": float(total_cost),
            "cost_per_work_rubles": float(cost_per_work),
            "total_tokens": total_input + total_output,
            "input_tokens": total_input,
            "output_tokens": total_output,
            "model": self.model,
            "avg_work_length": avg_work_length
        }


# =============================================================================
# УДОБНЫЕ ФУНКЦИИ
# =============================================================================

def grade_ege_essay(
    source_text: str,
    student_answer: str,
    subject: str = "Русский язык",
    provider: str = 'deepseek',
    use_cache: bool = True
) -> ExamGradingResult:
    """
    Проверяет сочинение ЕГЭ по русскому языку (задание 27)
    
    Args:
        source_text: исходный текст для сочинения
        student_answer: сочинение ученика
        subject: предмет (по умолчанию "Русский язык")
        provider: провайдер AI ('deepseek' или 'openai')
        use_cache: использовать кэш
    
    Returns:
        ExamGradingResult с оценкой по всем критериям
    """
    service = ExamAIGradingService(provider=provider)
    return service.grade_exam_work_sync(
        source_text=source_text,
        student_answer=student_answer,
        criteria_key="russian_27",
        exam_type="ЕГЭ",
        subject=subject,
        use_cache=use_cache
    )


def estimate_exam_grading_cost(
    num_students: int,
    exam_type: str = "ЕГЭ",
    task_type: str = "russian_27",
    avg_length: int = 2000
) -> Dict[str, any]:
    """
    Оценивает стоимость проверки работ для класса
    
    Args:
        num_students: количество учеников
        exam_type: "ЕГЭ" или "ОГЭ"
        task_type: тип задания ("russian_27", "social_29", etc.)
        avg_length: средняя длина работы
    
    Returns:
        dict: информация о стоимости
    """
    service = ExamAIGradingService()
    estimate = service.estimate_cost(
        num_works=num_students,
        avg_work_length=avg_length,
        criteria_key=task_type
    )
    
    estimate["exam_type"] = exam_type
    estimate["task_type"] = task_type
    
    return estimate


# =============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# =============================================================================

if __name__ == "__main__":
    from .ai_grading_examples import EXAMPLE_1_SOURCE, EXAMPLE_1_STUDENT_ANSWER
    
    print("=== Пример проверки сочинения ЕГЭ ===\n")
    
    result = grade_ege_essay(
        source_text=EXAMPLE_1_SOURCE,
        student_answer=EXAMPLE_1_STUDENT_ANSWER,
        provider='deepseek'
    )
    
    print(f"Оценка: {result.total_score} / {result.max_score}")
    print(f"Стоимость: {result.cost_rubles} ₽")
    print(f"Модель: {result.model_used}")
    print(f"Токены: {result.tokens_used}")
    
    print(f"\n=== ИТОГ ===")
    print(result.summary)
    
    print(f"\n=== СИЛЬНЫЕ СТОРОНЫ ===")
    for s in result.strengths:
        print(f"✓ {s}")
    
    print(f"\n=== ЧТО УЛУЧШИТЬ ===")
    for w in result.weaknesses:
        print(f"✗ {w}")
    
    print(f"\n=== ПРИМЕРЫ ОШИБОК ===")
    for err in result.examples_of_errors[:5]:  # показываем первые 5
        print(f"- [{err['type']}] {err['fragment']} → {err.get('correction', 'н/д')}")
    
    print("\n=== ОЦЕНКА СТОИМОСТИ ДЛЯ КЛАССА ===\n")
    
    estimate = estimate_exam_grading_cost(
        num_students=30,
        exam_type="ЕГЭ",
        task_type="russian_27",
        avg_length=2000
    )
    
    print(f"Количество работ: {estimate['num_works']}")
    print(f"Общая стоимость: {estimate['total_cost_rubles']:.2f} ₽")
    print(f"За 1 работу: {estimate['cost_per_work_rubles']:.4f} ₽")
    print(f"Токенов всего: {estimate['total_tokens']:,}")
