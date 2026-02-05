"""
AIService — RAG и LLM логика

Отвечает за:
- Поиск релевантных чанков в Knowledge Base
- Формирование промпта для LLM
- Получение ответа от LLM (DeepSeek/OpenAI)
- Парсинг структурированного ответа
"""

import logging
import json
import os
import httpx
from dataclasses import dataclass, field
from typing import List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Структурированный ответ от AI"""
    
    decision: str  # 'answer' | 'clarify' | 'action' | 'escalate'
    text: str = ''
    confidence: float = 0.0
    sources: List[dict] = field(default_factory=list)
    model: str = ''
    tokens_used: int = 0
    
    # Для action
    action_name: str = ''
    action_params: dict = field(default_factory=dict)
    
    # Для escalate
    reason: str = ''


class AIService:
    """
    Сервис AI для обработки сообщений.
    
    Pipeline:
    1. Поиск в Knowledge Base (RAG)
    2. Сборка промпта с контекстом
    3. Запрос к LLM
    4. Парсинг и валидация ответа
    """
    
    # Конфигурация
    DEFAULT_PROVIDER = 'deepseek'
    DEEPSEEK_MODEL = 'deepseek-chat'
    OPENAI_MODEL = 'gpt-4o-mini'
    
    TIMEOUT_SECONDS = 30
    MAX_TOKENS = 1000
    TEMPERATURE = 0.3  # Низкая температура для более предсказуемых ответов
    
    @classmethod
    async def process(
        cls,
        conversation,
        message,
        history: list,
    ) -> AIResponse:
        """
        Обработать сообщение пользователя.
        
        Args:
            conversation: Объект диалога
            message: Текущее сообщение пользователя
            history: Последние N сообщений для контекста
        
        Returns:
            AIResponse: Структурированный ответ
        """
        # 1. Поиск в Knowledge Base
        from .knowledge_service import KnowledgeService
        
        relevant_chunks = await KnowledgeService.search(
            query=message.content,
            language=conversation.language,
            limit=5,
        )
        
        # 2. Получаем доступные действия
        from ..models import ActionDefinition
        from asgiref.sync import sync_to_async
        
        available_actions = await sync_to_async(list)(
            ActionDefinition.objects.filter(is_active=True).values(
                'name', 'display_name', 'description', 'trigger_keywords', 'is_read_only'
            )
        )
        
        # 3. Формируем промпт
        prompt = cls._build_prompt(
            user_message=message.content,
            conversation_context=conversation.user_context,
            page_context={
                'url': conversation.page_url,
                'title': conversation.page_title,
            },
            history=history,
            knowledge_chunks=relevant_chunks,
            available_actions=available_actions,
            language=conversation.language,
            retry_count=conversation.ai_retry_count,
        )
        
        # 4. Запрос к LLM
        try:
            raw_response = await cls._call_llm(prompt, conversation.language)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return AIResponse(
                decision='escalate',
                reason=f"LLM error: {str(e)}",
            )
        
        # 5. Парсинг ответа
        return cls._parse_response(raw_response)
    
    @classmethod
    async def generate_action_response(
        cls,
        conversation,
        action_name: str,
        action_result: dict,
    ) -> AIResponse:
        """
        Сгенерировать ответ на основе результата действия.
        
        Args:
            conversation: Объект диалога
            action_name: Название выполненного действия
            action_result: Результат выполнения
        
        Returns:
            AIResponse: Ответ для пользователя
        """
        prompt = cls._build_action_response_prompt(
            action_name=action_name,
            action_result=action_result,
            language=conversation.language,
        )
        
        try:
            raw_response = await cls._call_llm(prompt, conversation.language)
            return AIResponse(
                decision='answer',
                text=raw_response.get('text', str(action_result)),
                confidence=0.9,
            )
        except Exception as e:
            # Fallback: просто показываем результат
            logger.warning(f"Failed to generate action response: {e}")
            return AIResponse(
                decision='answer',
                text=action_result.get('message', 'Действие выполнено.'),
                confidence=0.7,
            )
    
    # =========================================================================
    # Private methods
    # =========================================================================
    
    @classmethod
    def _build_prompt(
        cls,
        user_message: str,
        conversation_context: dict,
        page_context: dict,
        history: list,
        knowledge_chunks: list,
        available_actions: list,
        language: str,
        retry_count: int,
    ) -> str:
        """Сформировать промпт для LLM"""
        
        # Системный промпт
        system_prompt = cls._get_system_prompt(language)
        
        # Контекст пользователя
        user_info = f"""
## Контекст пользователя
- Роль: {conversation_context.get('role', 'unknown')}
- Email: {conversation_context.get('email', 'unknown')}
- Страница: {page_context.get('title', 'unknown')} ({page_context.get('url', '')})
"""
        
        if 'subscription' in conversation_context:
            sub = conversation_context['subscription']
            user_info += f"- Подписка: {sub.get('status', 'unknown')}\n"
        
        # История диалога
        history_text = "\n## История диалога\n"
        for msg in history[-6:]:  # Последние 6 сообщений
            sender = {
                'user': '👤 Пользователь',
                'ai': '🤖 AI',
                'admin': '👨‍💼 Оператор',
                'system': '⚙️ Система',
            }.get(msg.sender_type, msg.sender_type)
            history_text += f"{sender}: {msg.content[:500]}\n"
        
        # Релевантные знания (RAG)
        knowledge_text = ""
        if knowledge_chunks:
            knowledge_text = "\n## Релевантная информация из базы знаний\n"
            for chunk in knowledge_chunks:
                knowledge_text += f"---\n[{chunk.get('title', 'Doc')}]\n{chunk.get('content', '')}\n"
        
        # Доступные действия
        actions_text = "\n## Доступные автоматические действия\n"
        if available_actions:
            for action in available_actions:
                actions_text += f"- `{action['name']}`: {action['description'][:100]}\n"
        else:
            actions_text += "Нет доступных действий.\n"
        
        # Инструкция
        instruction = f"""
## Текущее сообщение пользователя
{user_message}

## Инструкция
Проанализируй сообщение пользователя и выбери ОДНО действие:

1. **answer** — ты можешь ответить на вопрос (есть информация в базе знаний или это общий вопрос)
2. **clarify** — нужно уточнить детали у пользователя (уже запрошено {retry_count} раз, максимум 2)
3. **action** — нужно выполнить автоматическое действие для диагностики или решения
4. **escalate** — не можешь помочь, нужен человек (сложная проблема, личные данные, жалоба)

Ответь в формате JSON:
```json
{{
    "decision": "answer|clarify|action|escalate",
    "text": "Текст ответа пользователю на {'английском' if language == 'en' else 'русском'} языке",
    "confidence": 0.0-1.0,
    "action_name": "имя_действия (только для decision=action)",
    "action_params": {{}},
    "reason": "причина (только для decision=escalate)"
}}
```

ВАЖНО:
- Если retry_count >= 2 и ты не уверен — эскалируй, не мучай пользователя
- Не придумывай информацию — если не знаешь, скажи честно
- Для технических проблем сначала попробуй action (диагностика)
- Отвечай коротко и по делу
"""
        
        return f"{system_prompt}\n{user_info}\n{history_text}\n{knowledge_text}\n{actions_text}\n{instruction}"
    
    @classmethod
    def _get_system_prompt(cls, language: str) -> str:
        """Получить системный промпт"""
        if language == 'en':
            return """You are Lectio Concierge — an AI support assistant for Lectio LMS (Learning Management System).

Your role:
- Help teachers and students with platform usage
- Diagnose technical issues
- Answer questions about features
- Escalate complex issues to human support

Platform features:
- Online lessons with Zoom integration
- Lesson recordings storage
- Homework assignments with auto-grading
- Student groups and schedules
- Subscription payments (YooKassa)

Be friendly, concise, and helpful. If unsure — ask clarifying questions or escalate."""
        
        return """Ты — Lectio Concierge, AI-ассистент поддержки для LMS Lectio (система управления обучением).

Твоя роль:
- Помогать преподавателям и студентам с использованием платформы
- Диагностировать технические проблемы
- Отвечать на вопросы о функциях
- Передавать сложные вопросы операторам

Функции платформы:
- Онлайн-уроки с интеграцией Zoom
- Хранение записей уроков
- Домашние задания с автопроверкой
- Группы студентов и расписание
- Оплата подписки (YooKassa)

Будь дружелюбным, кратким и полезным. Если не уверен — задай уточняющие вопросы или передай оператору."""
    
    @classmethod
    def _build_action_response_prompt(
        cls,
        action_name: str,
        action_result: dict,
        language: str,
    ) -> str:
        """Промпт для генерации ответа по результату действия"""
        
        lang_instruction = "in English" if language == 'en' else "на русском языке"
        
        return f"""Результат выполнения действия `{action_name}`:

```json
{json.dumps(action_result, ensure_ascii=False, indent=2)}
```

Сформулируй понятный ответ для пользователя {lang_instruction}.
Если есть проблема — объясни её и предложи решение.
Если всё в порядке — подтверди это.

Ответь в формате JSON:
```json
{{
    "text": "Ответ пользователю"
}}
```"""
    
    @classmethod
    async def _call_llm(cls, prompt: str, language: str) -> dict:
        """Вызвать LLM API"""
        provider = os.getenv('CONCIERGE_AI_PROVIDER', cls.DEFAULT_PROVIDER)
        
        if provider == 'deepseek':
            return await cls._call_deepseek(prompt)
        elif provider == 'openai':
            return await cls._call_openai(prompt)
        else:
            raise ValueError(f"Unknown AI provider: {provider}")
    
    @classmethod
    async def _call_deepseek(cls, prompt: str) -> dict:
        """Вызвать DeepSeek API"""
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured")
        
        async with httpx.AsyncClient(timeout=cls.TIMEOUT_SECONDS) as client:
            response = await client.post(
                'https://api.deepseek.com/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': cls.DEEPSEEK_MODEL,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': cls.MAX_TOKENS,
                    'temperature': cls.TEMPERATURE,
                    'response_format': {'type': 'json_object'},
                },
            )
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content']
            return json.loads(content)
    
    @classmethod
    async def _call_openai(cls, prompt: str) -> dict:
        """Вызвать OpenAI API"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        async with httpx.AsyncClient(timeout=cls.TIMEOUT_SECONDS) as client:
            response = await client.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': cls.OPENAI_MODEL,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': cls.MAX_TOKENS,
                    'temperature': cls.TEMPERATURE,
                    'response_format': {'type': 'json_object'},
                },
            )
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content']
            return json.loads(content)
    
    @classmethod
    def _parse_response(cls, raw: dict) -> AIResponse:
        """Распарсить ответ LLM в AIResponse"""
        try:
            return AIResponse(
                decision=raw.get('decision', 'escalate'),
                text=raw.get('text', ''),
                confidence=float(raw.get('confidence', 0.5)),
                action_name=raw.get('action_name', ''),
                action_params=raw.get('action_params', {}),
                reason=raw.get('reason', ''),
            )
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}, raw: {raw}")
            return AIResponse(
                decision='escalate',
                reason=f"Failed to parse AI response: {e}",
            )
