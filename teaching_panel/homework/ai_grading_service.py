"""
AI Grading Service - проверка текстовых ответов с помощью AI

Поддерживаемые провайдеры:
- DeepSeek (рекомендуется, дешевый и качественный)
- OpenAI (GPT-4o-mini, GPT-4o)

Настройка:
В settings.py добавьте:
    DEEPSEEK_API_KEY = 'sk-...'
    OPENAI_API_KEY = 'sk-...'
"""

import json
import logging
import httpx
from typing import Optional
from dataclasses import dataclass
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class AIGradingResult:
    """Результат AI проверки"""
    score: int  # Оценка в баллах (0 - max_points)
    max_points: int  # Максимум баллов за вопрос
    feedback: str  # Комментарий AI
    confidence: float  # Уверенность AI (0.0 - 1.0)
    error: Optional[str] = None  # Ошибка, если была


class AIGradingService:
    """Сервис для AI проверки ответов на вопросы"""
    
    # Системный промпт для проверки
    SYSTEM_PROMPT = """Ты - опытный преподаватель, проверяющий домашние задания студентов.

Твоя задача - оценить ответ студента на вопрос.

ВАЖНЫЕ ПРАВИЛА:
1. Оценивай по существу, не придирайся к мелочам
2. Частично правильные ответы заслуживают частичных баллов
3. Давай конструктивную обратную связь
4. Будь доброжелательным, но объективным
5. Если ответ пустой или бессмысленный - 0 баллов

Отвечай ТОЛЬКО в формате JSON:
{
    "score": <число от 0 до max_points>,
    "feedback": "<краткий комментарий на русском языке>",
    "confidence": <число от 0.0 до 1.0>
}"""

    def __init__(self, provider: str = 'deepseek'):
        self.provider = provider
        self.timeout = 30  # секунд
        
    def _get_api_config(self) -> tuple[str, str, str]:
        """Возвращает (api_url, api_key, model) для провайдера"""
        if self.provider == 'deepseek':
            return (
                'https://api.deepseek.com/v1/chat/completions',
                getattr(settings, 'DEEPSEEK_API_KEY', ''),
                'deepseek-chat'  # Или deepseek-reasoner для более сложных задач
            )
        elif self.provider == 'openai':
            return (
                'https://api.openai.com/v1/chat/completions',
                getattr(settings, 'OPENAI_API_KEY', ''),
                'gpt-4o-mini'  # Дешевая и быстрая модель
            )
        else:
            raise ValueError(f"Неизвестный провайдер: {self.provider}")
    
    def _build_user_prompt(
        self,
        question_text: str,
        student_answer: str,
        max_points: int,
        correct_answer: Optional[str] = None,
        teacher_context: Optional[str] = None
    ) -> str:
        """Формирует промпт для AI"""
        parts = [
            f"ВОПРОС:\n{question_text}",
            f"\nМАКСИМУМ БАЛЛОВ: {max_points}",
        ]
        
        if correct_answer:
            parts.append(f"\nЭТАЛОННЫЙ ОТВЕТ (для справки):\n{correct_answer}")
        
        if teacher_context:
            parts.append(f"\nКОНТЕКСТ ОТ ПРЕПОДАВАТЕЛЯ:\n{teacher_context}")
        
        parts.append(f"\nОТВЕТ СТУДЕНТА:\n{student_answer if student_answer.strip() else '(пустой ответ)'}")
        
        return "\n".join(parts)
    
    async def grade_answer_async(
        self,
        question_text: str,
        student_answer: str,
        max_points: int,
        correct_answer: Optional[str] = None,
        teacher_context: Optional[str] = None
    ) -> AIGradingResult:
        """Асинхронная проверка ответа через AI API"""
        
        api_url, api_key, model = self._get_api_config()
        
        if not api_key:
            return AIGradingResult(
                score=0,
                max_points=max_points,
                feedback="AI проверка недоступна: не настроен API ключ",
                confidence=0.0,
                error=f"Missing API key for {self.provider}"
            )
        
        user_prompt = self._build_user_prompt(
            question_text=question_text,
            student_answer=student_answer,
            max_points=max_points,
            correct_answer=correct_answer,
            teacher_context=teacher_context
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.3,  # Низкая для более стабильных оценок
                        "max_tokens": 500
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Извлекаем ответ AI
                ai_text = data['choices'][0]['message']['content'].strip()
                
                # Парсим JSON из ответа
                result = self._parse_ai_response(ai_text, max_points)
                return result
                
        except httpx.TimeoutException:
            logger.warning(f"AI grading timeout for provider {self.provider}")
            return AIGradingResult(
                score=0,
                max_points=max_points,
                feedback="AI проверка: таймаут, требуется ручная проверка",
                confidence=0.0,
                error="Timeout"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"AI grading HTTP error: {e.response.status_code} - {e.response.text}")
            return AIGradingResult(
                score=0,
                max_points=max_points,
                feedback="AI проверка: ошибка API, требуется ручная проверка",
                confidence=0.0,
                error=f"HTTP {e.response.status_code}"
            )
        except Exception as e:
            logger.exception(f"AI grading error: {e}")
            return AIGradingResult(
                score=0,
                max_points=max_points,
                feedback="AI проверка: ошибка, требуется ручная проверка",
                confidence=0.0,
                error=str(e)
            )
    
    def grade_answer_sync(
        self,
        question_text: str,
        student_answer: str,
        max_points: int,
        correct_answer: Optional[str] = None,
        teacher_context: Optional[str] = None
    ) -> AIGradingResult:
        """Синхронная проверка ответа через AI API (для Django views)"""
        
        api_url, api_key, model = self._get_api_config()
        
        if not api_key:
            return AIGradingResult(
                score=0,
                max_points=max_points,
                feedback="AI проверка недоступна: не настроен API ключ",
                confidence=0.0,
                error=f"Missing API key for {self.provider}"
            )
        
        user_prompt = self._build_user_prompt(
            question_text=question_text,
            student_answer=student_answer,
            max_points=max_points,
            correct_answer=correct_answer,
            teacher_context=teacher_context
        )
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 500
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                ai_text = data['choices'][0]['message']['content'].strip()
                result = self._parse_ai_response(ai_text, max_points)
                return result
                
        except httpx.TimeoutException:
            logger.warning(f"AI grading timeout for provider {self.provider}")
            return AIGradingResult(
                score=0,
                max_points=max_points,
                feedback="AI проверка: таймаут, требуется ручная проверка",
                confidence=0.0,
                error="Timeout"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"AI grading HTTP error: {e.response.status_code}")
            return AIGradingResult(
                score=0,
                max_points=max_points,
                feedback="AI проверка: ошибка API, требуется ручная проверка",
                confidence=0.0,
                error=f"HTTP {e.response.status_code}"
            )
        except Exception as e:
            logger.exception(f"AI grading error: {e}")
            return AIGradingResult(
                score=0,
                max_points=max_points,
                feedback="AI проверка: ошибка, требуется ручная проверка",
                confidence=0.0,
                error=str(e)
            )
    
    def _parse_ai_response(self, ai_text: str, max_points: int) -> AIGradingResult:
        """Парсит JSON ответ от AI"""
        try:
            # Иногда AI оборачивает JSON в ```json ... ```
            if '```json' in ai_text:
                ai_text = ai_text.split('```json')[1].split('```')[0]
            elif '```' in ai_text:
                ai_text = ai_text.split('```')[1].split('```')[0]
            
            data = json.loads(ai_text.strip())
            
            score = int(data.get('score', 0))
            # Ограничиваем score в пределах [0, max_points]
            score = max(0, min(score, max_points))
            
            feedback = str(data.get('feedback', 'Без комментария'))
            confidence = float(data.get('confidence', 0.5))
            confidence = max(0.0, min(1.0, confidence))
            
            return AIGradingResult(
                score=score,
                max_points=max_points,
                feedback=feedback,
                confidence=confidence
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse AI response: {ai_text[:200]}...")
            # Если не удалось распарсить - возвращаем 0 с требованием ручной проверки
            return AIGradingResult(
                score=0,
                max_points=max_points,
                feedback=f"AI ответ не распознан, требуется ручная проверка. Ответ AI: {ai_text[:100]}...",
                confidence=0.0,
                error="Parse error"
            )


def grade_text_answer(
    question_text: str,
    student_answer: str,
    max_points: int,
    provider: str = 'deepseek',
    correct_answer: Optional[str] = None,
    teacher_context: Optional[str] = None
) -> AIGradingResult:
    """
    Удобная функция для проверки текстового ответа.
    
    Args:
        question_text: Текст вопроса
        student_answer: Ответ студента
        max_points: Максимум баллов за вопрос
        provider: 'deepseek' или 'openai'
        correct_answer: Эталонный ответ (опционально)
        teacher_context: Дополнительный контекст от преподавателя
    
    Returns:
        AIGradingResult с оценкой, комментарием и уверенностью
    """
    service = AIGradingService(provider=provider)
    return service.grade_answer_sync(
        question_text=question_text,
        student_answer=student_answer,
        max_points=max_points,
        correct_answer=correct_answer,
        teacher_context=teacher_context
    )
