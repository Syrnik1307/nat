"""
AI Grading Service — проверка ДЗ через пул Gemini API ключей.

Поддерживаемые провайдеры:
- Google Gemini (рекомендуется, бесплатный AI Studio)
- DeepSeek (дешёвый и качественный)
- OpenAI (GPT-4o-mini, GPT-4o)

Feature flag: AI_GRADING_ENABLED=1 (default='0', всё выключено)

Архитектура:
1. AIGradingService — ядро: round-robin ключей, batch-проверка, трекинг токенов
2. GeminiAPIKey (models.py) — пул ключей с дневными лимитами
3. AIGradingJob (models.py) — очередь задач для Celery
4. AIGradingUsage (models.py) — месячный расход по учителям
"""

import json
import logging
import httpx
from datetime import date
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field
from django.conf import settings
from django.utils import timezone
from django.db.models import F

logger = logging.getLogger(__name__)


def is_ai_grading_enabled() -> bool:
    """Проверяет feature flag. Если False — весь AI-grading молча отключен."""
    return getattr(settings, 'AI_GRADING_ENABLED', False)


@dataclass
class AIGradingResult:
    """Результат AI проверки одного ответа."""
    question_id: int = 0
    score: int = 0           # 0 — max_points
    max_points: int = 0
    feedback: str = ''
    confidence: float = 0.0  # 0.0 — 1.0
    error: Optional[str] = None


@dataclass
class BatchGradingResult:
    """Результат AI проверки целой работы (batch)."""
    results: List[AIGradingResult] = field(default_factory=list)
    tokens_input: int = 0
    tokens_output: int = 0
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class NoAvailableKeyError(Exception):
    """Все API-ключи исчерпаны или отключены."""
    pass


class TeacherLimitExceededError(Exception):
    """Учитель превысил месячный лимит токенов."""
    pass


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
BATCH_SYSTEM_PROMPT = """Ты — опытный преподаватель, проверяющий домашние задания студентов.

Тебе будет дано задание с несколькими вопросами и ответами студента.
Оцени каждый ответ ОТДЕЛЬНО.

ВАЖНЫЕ ПРАВИЛА:
1. Оценивай по существу, не придирайся к несущественным мелочам
2. Частично правильные ответы заслуживают частичных баллов
3. Давай конструктивную, короткую обратную связь (1-3 предложения)
4. Будь доброжелательным, но объективным
5. Если ответ пустой или бессмысленный — 0 баллов
6. Если ответ на другом языке — проверяй содержание, не язык

Отвечай СТРОГО в формате JSON (массив объектов):
[
  {
    "question_id": <int>,
    "score": <число от 0 до max_points>,
    "feedback": "<комментарий на русском языке, 1-3 предложения>",
    "confidence": <число от 0.0 до 1.0>
  }
]

Ответь ТОЛЬКО JSON, без markdown-блоков и пояснений."""

SINGLE_SYSTEM_PROMPT = """Ты — опытный преподаватель, проверяющий домашние задания студентов.

Твоя задача — оценить ответ студента на вопрос.

ВАЖНЫЕ ПРАВИЛА:
1. Оценивай по существу, не придирайся к мелочам
2. Частично правильные ответы заслуживают частичных баллов
3. Давай конструктивную обратную связь
4. Будь доброжелательным, но объективным
5. Если ответ пустой или бессмысленный — 0 баллов

Отвечай ТОЛЬКО в формате JSON:
{
    "score": <число от 0 до max_points>,
    "feedback": "<краткий комментарий на русском языке>",
    "confidence": <число от 0.0 до 1.0>
}"""


class AIGradingService:
    """Сервис для AI проверки ответов.

    Поддерживает:
    - Batch-проверку целой работы (один API-запрос = все needs_manual_review ответы)
    - Round-robin пул Gemini API ключей с авто-отключением
    - Трекинг токенов (input/output) из usageMetadata Gemini
    - Fallback на DeepSeek/OpenAI
    """

    TIMEOUT = 60  # секунд (batch может быть длиннее)

    def __init__(self, provider: str = 'gemini'):
        self.provider = provider

    # -----------------------------------------------------------------------
    # API config per provider
    # -----------------------------------------------------------------------
    @staticmethod
    def _get_provider_config(provider: str) -> Tuple[str, str, str]:
        """Возвращает (api_url, api_key, model) для провайдера (DeepSeek/OpenAI)."""
        if provider == 'deepseek':
            return (
                'https://api.deepseek.com/v1/chat/completions',
                getattr(settings, 'DEEPSEEK_API_KEY', ''),
                'deepseek-chat',
            )
        elif provider == 'openai':
            return (
                'https://api.openai.com/v1/chat/completions',
                getattr(settings, 'OPENAI_API_KEY', ''),
                'gpt-4o-mini',
            )
        raise ValueError(f"Unknown non-Gemini provider: {provider}")

    # -----------------------------------------------------------------------
    # Key pool management
    # -----------------------------------------------------------------------
    @staticmethod
    def select_api_key():
        """Выбирает следующий доступный ключ Gemini из пула (round-robin)."""
        from .models import GeminiAPIKey

        now = timezone.now()
        today = now.date()

        # Сброс дневных счётчиков если дата сменилась
        GeminiAPIKey.objects.filter(is_active=True).exclude(
            last_reset_date=today
        ).update(
            requests_used_today=0,
            tokens_used_today=0,
            last_reset_date=today,
        )

        # Ищем доступный ключ: active, не disabled, в пределах лимитов
        candidates = GeminiAPIKey.objects.filter(
            is_active=True,
        ).exclude(
            disabled_until__gt=now,
        ).filter(
            requests_used_today__lt=F('daily_request_limit'),
            tokens_used_today__lt=F('daily_token_limit'),
        ).order_by('-priority', 'requests_used_today', 'id')

        key = candidates.first()
        if not key:
            raise NoAvailableKeyError(
                "Все Gemini API ключи исчерпаны или отключены"
            )
        return key

    @staticmethod
    def record_key_usage(key, tokens_in: int, tokens_out: int):
        """Обновляет счётчики на ключе после успешного запроса."""
        from .models import GeminiAPIKey
        GeminiAPIKey.objects.filter(pk=key.pk).update(
            requests_used_today=F('requests_used_today') + 1,
            tokens_used_today=F('tokens_used_today') + tokens_in + tokens_out,
            consecutive_errors=0,
            last_error='',
        )

    @staticmethod
    def record_key_error(key, error_msg: str):
        """Помечает ошибку ключа. При 3+ подряд — отключает на 5 минут."""
        from .models import GeminiAPIKey
        from datetime import timedelta

        new_errors = key.consecutive_errors + 1
        updates = {
            'consecutive_errors': new_errors,
            'last_error': error_msg[:500],
        }
        if new_errors >= 3:
            updates['disabled_until'] = timezone.now() + timedelta(minutes=5)
            logger.warning(
                "Gemini key '%s' disabled for 5 min after %d consecutive errors: %s",
                key.label, new_errors, error_msg[:200],
            )
        GeminiAPIKey.objects.filter(pk=key.pk).update(**updates)

    # -----------------------------------------------------------------------
    # Teacher usage tracking
    # -----------------------------------------------------------------------
    @staticmethod
    def check_teacher_limit(teacher) -> bool:
        """True если учитель НЕ превысил лимит. False — лимит исчерпан."""
        from .models import AIGradingUsage
        month_start = date.today().replace(day=1)
        usage, _ = AIGradingUsage.objects.get_or_create(
            teacher=teacher, month=month_start,
        )
        return not usage.is_limit_exceeded

    @staticmethod
    def record_teacher_usage(teacher, tokens: int):
        """Добавляет расход токенов учителю за текущий месяц."""
        from .models import AIGradingUsage
        month_start = date.today().replace(day=1)
        usage, _ = AIGradingUsage.objects.get_or_create(
            teacher=teacher, month=month_start,
        )
        AIGradingUsage.objects.filter(pk=usage.pk).update(
            tokens_used=F('tokens_used') + tokens,
            requests_count=F('requests_count') + 1,
            submissions_graded=F('submissions_graded') + 1,
        )

    @staticmethod
    def get_teacher_remaining_tokens(teacher) -> int:
        """Сколько токенов осталось у учителя в этом месяце."""
        from .models import AIGradingUsage
        month_start = date.today().replace(day=1)
        usage, _ = AIGradingUsage.objects.get_or_create(
            teacher=teacher, month=month_start,
        )
        return usage.tokens_remaining

    # -----------------------------------------------------------------------
    # Batch grading (whole submission)
    # -----------------------------------------------------------------------
    def grade_submission_batch(
        self,
        submission,
        teacher_prompt: str = '',
    ) -> BatchGradingResult:
        """
        Проверяет все needs_manual_review ответы целой работы одним запросом.

        Args:
            submission: StudentSubmission instance (с prefetch answers/questions)
            teacher_prompt: доп. инструкции от учителя

        Returns:
            BatchGradingResult с оценками по каждому вопросу + token usage
        """
        answers = list(
            submission.answers
            .filter(needs_manual_review=True)
            .select_related('question')
        )
        if not answers:
            return BatchGradingResult(error="No answers need AI review")

        # Build prompt
        user_prompt = self._build_batch_prompt(submission, answers, teacher_prompt)

        # Route to correct provider
        if self.provider == 'gemini':
            return self._call_gemini_batch(user_prompt, answers)
        else:
            return self._call_openai_compatible_batch(user_prompt, answers)

    def _build_batch_prompt(self, submission, answers, teacher_prompt: str) -> str:
        """Формирует user prompt для batch-проверки."""
        hw = submission.homework
        parts = [
            f"ЗАДАНИЕ: {hw.title}",
        ]
        if hw.description:
            parts.append(f"ОПИСАНИЕ: {hw.description}")
        if teacher_prompt:
            parts.append(f"\nИНСТРУКЦИИ ПРЕПОДАВАТЕЛЯ:\n{teacher_prompt}")

        student_name = ''
        if hasattr(submission.student, 'get_full_name'):
            student_name = submission.student.get_full_name()
        student_name = student_name or submission.student.email
        parts.append(f"\nСТУДЕНТ: {student_name}")
        parts.append(f"\n--- ВОПРОСЫ И ОТВЕТЫ (проверь каждый) ---\n")

        for ans in answers:
            q = ans.question
            q_text = q.prompt or "(без текста вопроса)"
            a_text = ans.text_answer or "(пустой ответ)"

            # Для FILE_UPLOAD — описываем что файл загружен
            if q.question_type == 'FILE_UPLOAD' and ans.attachments:
                a_text = f"[Загружены файлы: {len(ans.attachments)} шт.] {a_text}"

            correct_answer = ''
            if q.config and isinstance(q.config, dict):
                correct_answer = q.config.get('correctAnswer', '')

            parts.append(f"ВОПРОС #{q.id} (макс. {q.points} баллов, тип: {q.question_type}):")
            parts.append(f"  Текст: {q_text}")
            if correct_answer:
                parts.append(f"  Эталонный ответ: {correct_answer}")
            if q.explanation:
                parts.append(f"  Пояснение: {q.explanation}")
            parts.append(f"  Ответ студента: {a_text}")
            parts.append("")

        return "\n".join(parts)

    # -----------------------------------------------------------------------
    # Gemini API call
    # -----------------------------------------------------------------------
    def _call_gemini_batch(self, user_prompt: str, answers) -> BatchGradingResult:
        """Вызывает Gemini API через AI Studio (query param key)."""
        try:
            api_key_obj = self.select_api_key()
        except NoAvailableKeyError as e:
            return BatchGradingResult(error=str(e))

        model = getattr(settings, 'AI_GRADING_GEMINI_MODEL', 'gemini-2.0-flash')
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent?key={api_key_obj.api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": BATCH_SYSTEM_PROMPT + "\n\n" + user_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
            },
        }

        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                resp = client.post(url, json=payload)

                if resp.status_code == 429:
                    self.record_key_error(api_key_obj, "429 Rate Limited")
                    return BatchGradingResult(error="Rate limited, retry later")

                resp.raise_for_status()
                data = resp.json()

            # Parse tokens from usageMetadata
            usage = data.get('usageMetadata', {})
            tokens_in = usage.get('promptTokenCount', 0)
            tokens_out = usage.get('candidatesTokenCount', 0)

            # Record usage on key
            self.record_key_usage(api_key_obj, tokens_in, tokens_out)

            # Extract text
            ai_text = (
                data.get('candidates', [{}])[0]
                .get('content', {})
                .get('parts', [{}])[0]
                .get('text', '')
            )

            results = self._parse_batch_response(ai_text, answers)
            return BatchGradingResult(
                results=results,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            err = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            self.record_key_error(api_key_obj, err)
            logger.error("Gemini API error: %s", err)
            return BatchGradingResult(error=err)
        except httpx.TimeoutException:
            self.record_key_error(api_key_obj, "Timeout")
            logger.warning("Gemini API timeout for key %s", api_key_obj.label)
            return BatchGradingResult(error="Timeout")
        except Exception as e:
            self.record_key_error(api_key_obj, str(e))
            logger.exception("Gemini API unexpected error")
            return BatchGradingResult(error=str(e))

    # -----------------------------------------------------------------------
    # OpenAI-compatible API call (DeepSeek, OpenAI)
    # -----------------------------------------------------------------------
    def _call_openai_compatible_batch(self, user_prompt: str, answers) -> BatchGradingResult:
        """Вызывает DeepSeek/OpenAI compatible API."""
        try:
            api_url, api_key, model = self._get_provider_config(self.provider)
        except ValueError as e:
            return BatchGradingResult(error=str(e))

        if not api_key:
            return BatchGradingResult(
                error=f"Missing API key for {self.provider}"
            )

        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                resp = client.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": BATCH_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2048,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            usage = data.get('usage', {})
            tokens_in = usage.get('prompt_tokens', 0)
            tokens_out = usage.get('completion_tokens', 0)

            ai_text = data['choices'][0]['message']['content'].strip()
            results = self._parse_batch_response(ai_text, answers)

            return BatchGradingResult(
                results=results,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                raw_response=data,
            )

        except httpx.TimeoutException:
            return BatchGradingResult(error="Timeout")
        except httpx.HTTPStatusError as e:
            return BatchGradingResult(error=f"HTTP {e.response.status_code}")
        except Exception as e:
            logger.exception("AI grading error (%s)", self.provider)
            return BatchGradingResult(error=str(e))

    # -----------------------------------------------------------------------
    # Response parsing
    # -----------------------------------------------------------------------
    def _parse_batch_response(
        self, ai_text: str, answers
    ) -> List[AIGradingResult]:
        """Парсит JSON-массив оценок от AI."""
        answer_map = {}
        for ans in answers:
            answer_map[ans.question_id] = ans

        try:
            text = ai_text.strip()
            if text.startswith('```'):
                lines = text.split('\n')
                lines = [l for l in lines if not l.strip().startswith('```')]
                text = '\n'.join(lines)

            items = json.loads(text)
            if not isinstance(items, list):
                items = [items]

            results = []
            for item in items:
                qid = int(item.get('question_id', 0))
                ans = answer_map.get(qid)
                max_pts = ans.question.points if ans else 0

                score = int(item.get('score', 0))
                score = max(0, min(score, max_pts))

                confidence = float(item.get('confidence', 0.5))
                confidence = max(0.0, min(1.0, confidence))

                feedback = str(item.get('feedback', 'Без комментария'))

                results.append(AIGradingResult(
                    question_id=qid,
                    score=score,
                    max_points=max_pts,
                    feedback=feedback,
                    confidence=confidence,
                ))

            return results

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to parse AI batch response: %s", ai_text[:300])
            return [
                AIGradingResult(
                    question_id=ans.question_id,
                    score=0,
                    max_points=ans.question.points,
                    feedback="AI ответ не распознан, требуется ручная проверка.",
                    confidence=0.0,
                    error=f"Parse error: {e}",
                )
                for ans in answers
            ]

    # -----------------------------------------------------------------------
    # Legacy single-answer grading (backwards compatibility)
    # -----------------------------------------------------------------------
    def grade_answer_sync(
        self,
        question_text: str,
        student_answer: str,
        max_points: int,
        correct_answer: Optional[str] = None,
        teacher_context: Optional[str] = None,
    ) -> AIGradingResult:
        """Синхронная проверка одного ответа (legacy, используется в Answer.evaluate)."""
        if self.provider == 'gemini':
            return self._grade_single_gemini(
                question_text, student_answer, max_points,
                correct_answer, teacher_context,
            )
        return self._grade_single_openai_compat(
            question_text, student_answer, max_points,
            correct_answer, teacher_context,
        )

    def _grade_single_gemini(
        self, question_text, student_answer, max_points,
        correct_answer=None, teacher_context=None,
    ) -> AIGradingResult:
        """Проверка одного ответа через Gemini."""
        try:
            api_key_obj = self.select_api_key()
        except NoAvailableKeyError:
            return AIGradingResult(
                score=0, max_points=max_points,
                feedback="AI проверка недоступна: нет свободных ключей",
                confidence=0.0, error="NoAvailableKey",
            )

        prompt = self._build_single_prompt(
            question_text, student_answer, max_points,
            correct_answer, teacher_context,
        )
        model = getattr(settings, 'AI_GRADING_GEMINI_MODEL', 'gemini-2.0-flash')
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent?key={api_key_obj.api_key}"
        )

        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                resp = client.post(url, json={
                    "contents": [{"parts": [{"text": SINGLE_SYSTEM_PROMPT + "\n\n" + prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 500,
                        "responseMimeType": "application/json",
                    },
                })
                if resp.status_code == 429:
                    self.record_key_error(api_key_obj, "429 Rate Limited")
                    return AIGradingResult(
                        score=0, max_points=max_points,
                        feedback="AI rate limited, требуется ручная проверка",
                        confidence=0.0, error="429",
                    )
                resp.raise_for_status()
                data = resp.json()

            usage = data.get('usageMetadata', {})
            self.record_key_usage(
                api_key_obj,
                usage.get('promptTokenCount', 0),
                usage.get('candidatesTokenCount', 0),
            )

            ai_text = (
                data.get('candidates', [{}])[0]
                .get('content', {})
                .get('parts', [{}])[0]
                .get('text', '')
            )
            return self._parse_single_response(ai_text, max_points)

        except Exception as e:
            self.record_key_error(api_key_obj, str(e))
            logger.exception("Gemini single grading error")
            return AIGradingResult(
                score=0, max_points=max_points,
                feedback="AI проверка: ошибка, требуется ручная проверка",
                confidence=0.0, error=str(e),
            )

    def _grade_single_openai_compat(
        self, question_text, student_answer, max_points,
        correct_answer=None, teacher_context=None,
    ) -> AIGradingResult:
        """Проверка одного ответа через DeepSeek/OpenAI."""
        try:
            api_url, api_key, model = self._get_provider_config(self.provider)
        except ValueError as e:
            return AIGradingResult(
                score=0, max_points=max_points,
                feedback=str(e), confidence=0.0, error=str(e),
            )
        if not api_key:
            return AIGradingResult(
                score=0, max_points=max_points,
                feedback=f"AI проверка недоступна: нет ключа для {self.provider}",
                confidence=0.0, error=f"Missing key for {self.provider}",
            )

        prompt = self._build_single_prompt(
            question_text, student_answer, max_points,
            correct_answer, teacher_context,
        )
        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                resp = client.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": SINGLE_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 500,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            ai_text = data['choices'][0]['message']['content'].strip()
            return self._parse_single_response(ai_text, max_points)
        except Exception as e:
            logger.exception("AI single grading error (%s)", self.provider)
            return AIGradingResult(
                score=0, max_points=max_points,
                feedback="AI проверка: ошибка, требуется ручная проверка",
                confidence=0.0, error=str(e),
            )

    @staticmethod
    def _build_single_prompt(
        question_text, student_answer, max_points,
        correct_answer=None, teacher_context=None,
    ) -> str:
        parts = [f"ВОПРОС:\n{question_text}", f"\nМАКСИМУМ БАЛЛОВ: {max_points}"]
        if correct_answer:
            parts.append(f"\nЭТАЛОННЫЙ ОТВЕТ:\n{correct_answer}")
        if teacher_context:
            parts.append(f"\nКОНТЕКСТ ОТ ПРЕПОДАВАТЕЛЯ:\n{teacher_context}")
        answer_text = student_answer.strip() if student_answer else '(пустой ответ)'
        parts.append(f"\nОТВЕТ СТУДЕНТА:\n{answer_text}")
        return "\n".join(parts)

    @staticmethod
    def _parse_single_response(ai_text: str, max_points: int) -> AIGradingResult:
        try:
            text = ai_text.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]

            data = json.loads(text.strip())
            score = max(0, min(int(data.get('score', 0)), max_points))
            confidence = max(0.0, min(1.0, float(data.get('confidence', 0.5))))
            feedback = str(data.get('feedback', 'Без комментария'))

            return AIGradingResult(
                score=score,
                max_points=max_points,
                feedback=feedback,
                confidence=confidence,
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("Failed to parse single AI response: %s", ai_text[:200])
            return AIGradingResult(
                score=0, max_points=max_points,
                feedback="AI ответ не распознан, требуется ручная проверка",
                confidence=0.0, error="Parse error",
            )


# ---------------------------------------------------------------------------
# Convenience function (legacy compatibility)
# ---------------------------------------------------------------------------
def grade_text_answer(
    question_text: str,
    student_answer: str,
    max_points: int,
    provider: str = 'gemini',
    correct_answer: Optional[str] = None,
    teacher_context: Optional[str] = None,
) -> AIGradingResult:
    """Удобная функция для проверки одного текстового ответа."""
    service = AIGradingService(provider=provider)
    return service.grade_answer_sync(
        question_text=question_text,
        student_answer=student_answer,
        max_points=max_points,
        correct_answer=correct_answer,
        teacher_context=teacher_context,
    )
