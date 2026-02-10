import hmac
import hashlib
import json
import time
import logging
from decimal import Decimal

import httpx
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import StudentSubmission, Answer

logger = logging.getLogger(__name__)


# =============================================================================
# NOTIFICATION TASKS (existing)
# =============================================================================

@shared_task(name='homework.tasks.notify_student_graded')
def notify_student_graded(submission_id: int):
    try:
        submission = StudentSubmission.objects.select_related('student', 'homework').get(id=submission_id)
    except StudentSubmission.DoesNotExist:
        return
    
    student = submission.student
    subject = f"Проверено: {submission.homework.title}"
    total = submission.total_score or 0
    message = (
        f"Здравствуйте, {student.first_name or student.email}!\n\n"
        f"Ваша работа по заданию '{submission.homework.title}' была проверена.\n"
        f"Итоговый балл: {total}.\n\n"
        f"Зайдите в систему, чтобы увидеть подробности и комментарии."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [student.email],
        fail_silently=True,
    )


# =============================================================================
# AI GRADING TASKS — Isolated worker queue
# =============================================================================

# Circuit breaker state (Redis-backed)
CIRCUIT_BREAKER_KEY = 'ai_grading:circuit_breaker'
CIRCUIT_BREAKER_FAILURES_KEY = 'ai_grading:circuit_failures'
CIRCUIT_BREAKER_THRESHOLD = 5  # failures before OPEN
CIRCUIT_BREAKER_COOLDOWN = 60  # seconds before HALF-OPEN


def _get_redis():
    """Returns Redis connection from Celery broker."""
    import redis
    broker_url = settings.CELERY_BROKER_URL
    if broker_url.startswith('memory://'):
        return None
    return redis.from_url(broker_url)


def _check_circuit_breaker() -> str:
    """Returns circuit state: 'closed', 'open', or 'half-open'."""
    r = _get_redis()
    if not r:
        return 'closed'
    
    state = r.get(CIRCUIT_BREAKER_KEY)
    if state is None:
        return 'closed'
    return state.decode('utf-8')


def _record_circuit_failure():
    """Record a failure; if threshold reached, open the circuit."""
    r = _get_redis()
    if not r:
        return
    
    failures = r.incr(CIRCUIT_BREAKER_FAILURES_KEY)
    r.expire(CIRCUIT_BREAKER_FAILURES_KEY, 300)
    
    if failures >= CIRCUIT_BREAKER_THRESHOLD:
        r.setex(CIRCUIT_BREAKER_KEY, CIRCUIT_BREAKER_COOLDOWN, 'open')
        r.delete(CIRCUIT_BREAKER_FAILURES_KEY)
        logger.error(
            f"AI circuit breaker OPENED after {failures} failures. "
            f"Cooldown: {CIRCUIT_BREAKER_COOLDOWN}s"
        )


def _record_circuit_success():
    """Record a success; reset failure counter."""
    r = _get_redis()
    if not r:
        return
    r.delete(CIRCUIT_BREAKER_FAILURES_KEY)
    r.delete(CIRCUIT_BREAKER_KEY)


def _sign_payload(payload_bytes: bytes) -> str:
    """HMAC-SHA256 sign payload for callback."""
    return hmac.new(
        settings.AI_CALLBACK_SECRET.encode('utf-8'),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def _send_callback(callback_url: str, payload: dict):
    """Send grading result back to Django via internal callback."""
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    signature = _sign_payload(body)

    try:
        resp = httpx.post(
            callback_url,
            content=body,
            headers={
                'Content-Type': 'application/json',
                'X-AI-Signature': signature,
            },
            timeout=10.0,
            verify=True,
        )
        if resp.status_code != 200:
            logger.error(
                f"AI callback failed: status={resp.status_code}, "
                f"body={resp.text[:200]}"
            )
    except Exception as e:
        logger.exception(f"AI callback error: {e}")


def _call_ai_provider(provider: str, model: str, messages: list, timeout: int = 30) -> dict:
    """
    Call AI provider API. Returns raw response dict.
    
    Supports: deepseek, openai, mock.
    """
    if provider == 'mock':
        return _mock_ai_response(messages)

    if provider == 'deepseek':
        api_url = 'https://api.deepseek.com/v1/chat/completions'
        api_key = settings.DEEPSEEK_API_KEY
    elif provider == 'openai':
        api_url = 'https://api.openai.com/v1/chat/completions'
        api_key = settings.OPENAI_API_KEY
    else:
        raise ValueError(f"Unknown provider: {provider}")

    if not api_key:
        logger.warning(f"No API key for {provider}, falling back to mock")
        return _mock_ai_response(messages)

    resp = httpx.post(
        api_url,
        json={
            'model': model or ('deepseek-chat' if provider == 'deepseek' else 'gpt-4o-mini'),
            'messages': messages,
            'temperature': 0.3,
            'max_tokens': 500,
        },
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        timeout=float(timeout),
    )
    resp.raise_for_status()
    return resp.json()


def _mock_ai_response(messages: list) -> dict:
    """Mock provider for development without API key."""
    import random
    # Extract max_points from the user prompt
    user_msg = messages[-1].get('content', '') if messages else ''
    max_pts = 10
    if 'МАКСИМУМ БАЛЛОВ:' in user_msg:
        try:
            max_pts = int(user_msg.split('МАКСИМУМ БАЛЛОВ:')[1].strip().split('\n')[0])
        except (ValueError, IndexError):
            pass

    # Distribute points across criteria
    k1_max = max(1, int(max_pts * 0.5))
    k2_max = max(1, int(max_pts * 0.3))
    k3_max = max(1, max_pts - k1_max - k2_max)

    k1_score = random.randint(k1_max // 2, k1_max)
    k2_score = random.randint(k2_max // 2, k2_max)
    k3_score = random.randint(k3_max // 2, k3_max)
    score = k1_score + k2_score + k3_score
    confidence = round(random.uniform(0.65, 0.95), 2)

    return {
        'choices': [{
            'message': {
                'content': json.dumps({
                    'score': score,
                    'confidence': confidence,
                    'criteria': [
                        {'name': 'K1: Содержание', 'score': k1_score, 'max_score': k1_max, 'comment': '[MOCK] Ответ раскрывает тему достаточно полно'},
                        {'name': 'K2: Логика', 'score': k2_score, 'max_score': k2_max, 'comment': '[MOCK] Аргументация последовательная'},
                        {'name': 'K3: Оформление', 'score': k3_score, 'max_score': k3_max, 'comment': '[MOCK] Оформление приемлемое'},
                    ],
                    'strengths': ['[MOCK] Хорошее раскрытие основной идеи', '[MOCK] Структурированный ответ'],
                    'weaknesses': ['[MOCK] Недостаточно примеров'],
                    'recommendations': ['[MOCK] Добавить конкретные примеры для подкрепления аргументов'],
                    'summary': f'[MOCK] Ответ проверен автоматически. Итоговый балл: {score}/{max_pts}. Работа в целом хорошая, но есть возможности для улучшения.',
                }, ensure_ascii=False)
            }
        }],
        'usage': {
            'prompt_tokens': 350,
            'completion_tokens': 250,
            'total_tokens': 600,
        },
        '_mock': True,
    }


SYSTEM_PROMPT = """Ты - опытный преподаватель, проверяющий домашние задания студентов.

Твоя задача - оценить ответ студента и написать подробный структурированный ревью.

ВАЖНЫЕ ПРАВИЛА:
1. Оценивай по существу, не придирайся к мелочам
2. Частично правильные ответы заслуживают частичных баллов
3. Давай конструктивную обратную связь с конкретными примерами
4. Будь доброжелательным, но объективным
5. Если ответ пустой или бессмысленный - 0 баллов
6. Оценку разбивай по критериям, каждому критерию ставь баллы

КРИТЕРИИ ОЦЕНКИ (адаптируй под предмет и тип задания):
- K1: Содержание и полнота ответа (основная часть баллов)
- K2: Логика и аргументация (обоснованность выводов)
- K3: Грамотность и оформление (язык, структура)
Если задание по программированию, используй критерии:
- K1: Корректность решения (правильность кода/алгоритма)
- K2: Качество кода (читаемость, структура, best practices)
- K3: Эффективность (оптимальность решения)

Распредели max_points между критериями пропорционально их важности.
Сумма max_score по всем критериям ДОЛЖНА равняться max_points.

Отвечай ТОЛЬКО в формате JSON:
{
    "score": <итоговый балл от 0 до max_points>,
    "confidence": <уверенность от 0.0 до 1.0>,
    "criteria": [
        {"name": "K1: Содержание", "score": <балл>, "max_score": <макс балл>, "comment": "<что хорошо/плохо>"},
        {"name": "K2: Логика", "score": <балл>, "max_score": <макс балл>, "comment": "<что хорошо/плохо>"},
        {"name": "K3: Оформление", "score": <балл>, "max_score": <макс балл>, "comment": "<что хорошо/плохо>"}
    ],
    "strengths": ["<сильная сторона 1>", "<сильная сторона 2>"],
    "weaknesses": ["<ошибка/недочет 1>", "<ошибка/недочет 2>"],
    "recommendations": ["<рекомендация 1>", "<рекомендация 2>"],
    "summary": "<общий комментарий преподавателя, 2-4 предложения>"
}"""


SYSTEM_PROMPT_CODE = """Ты - опытный преподаватель программирования, проверяющий код студентов.

Твоя задача - оценить код студента и написать подробный код-ревью.

ВАЖНЫЕ ПРАВИЛА:
1. Оценивай корректность решения, качество кода и эффективность
2. Указывай конкретные строки/участки с проблемами
3. Предлагай конкретные улучшения
4. Если код не компилируется/не запускается - отметь это
5. Учитывай результаты тестов, если они предоставлены

Отвечай ТОЛЬКО в формате JSON:
{
    "score": <итоговый балл от 0 до max_points>,
    "confidence": <уверенность от 0.0 до 1.0>,
    "criteria": [
        {"name": "K1: Корректность", "score": <балл>, "max_score": <макс балл>, "comment": "<работает ли решение>"},
        {"name": "K2: Качество кода", "score": <балл>, "max_score": <макс балл>, "comment": "<читаемость, именование, структура>"},
        {"name": "K3: Эффективность", "score": <балл>, "max_score": <макс балл>, "comment": "<оптимальность, сложность>"}
    ],
    "strengths": ["<что студент сделал хорошо>"],
    "weaknesses": ["<ошибки и проблемы в коде>"],
    "recommendations": ["<конкретные улучшения>"],
    "summary": "<общий комментарий, 2-4 предложения>"
}"""


@shared_task(
    name='homework.tasks.process_ai_grading',
    bind=True,
    max_retries=3,
    default_retry_delay=4,
    soft_time_limit=60,
    time_limit=120,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_ai_grading(self, payload: dict):
    """
    Main AI grading task — runs in isolated 'ai_grading' queue.
    
    1. Check circuit breaker
    2. Build prompt from payload 
    3. Call AI provider (with retry + failover)
    4. Parse response
    5. Send callback to Django
    """
    task_id = payload.get('task_id', self.request.id)
    request = payload.get('grading_request', {})
    answer_id = request.get('answer_id')
    callback_url = payload.get('callback_url', settings.AI_CALLBACK_URL)

    logger.info(f"AI grading started: task={task_id}, answer={answer_id}")

    # Update status to 'processing'
    try:
        Answer.objects.filter(id=answer_id).update(ai_grading_status='processing')
    except Exception:
        pass

    # Check circuit breaker
    circuit_state = _check_circuit_breaker()
    if circuit_state == 'open':
        logger.warning(f"Circuit breaker OPEN, sending to DLQ: answer={answer_id}")
        _send_failure_callback(
            callback_url, task_id, answer_id,
            'CIRCUIT_BREAKER_OPEN',
            'Circuit breaker is open, AI provider temporarily unavailable'
        )
        return

    # Build prompt
    question = request.get('question', {})
    student = request.get('student_answer', {})
    config = request.get('grading_config', {})
    question_type = request.get('question_type', 'TEXT')

    # Choose system prompt based on question type
    system_prompt = SYSTEM_PROMPT_CODE if question_type == 'CODE' else SYSTEM_PROMPT

    # Add custom teacher instructions if provided
    custom_prompt = config.get('custom_prompt')
    if custom_prompt:
        system_prompt += f"\n\nДОПОЛНИТЕЛЬНЫЕ ИНСТРУКЦИИ ПРЕПОДАВАТЕЛЯ:\n{custom_prompt}"

    prompt_parts = [
        f"ВОПРОС:\n{question.get('prompt', '')}",
        f"\nМАКСИМУМ БАЛЛОВ: {question.get('max_points', 10)}",
        f"\nТИП ЗАДАНИЯ: {question_type}",
    ]
    if question.get('correct_answer'):
        prompt_parts.append(f"\nЭТАЛОННЫЙ ОТВЕТ:\n{question['correct_answer']}")
    if question.get('subject_context'):
        prompt_parts.append(f"\nКОНТЕКСТ:\n{question['subject_context']}")

    student_text = student.get('text', '').strip() or '(пустой ответ)'
    prompt_parts.append(f"\nОТВЕТ СТУДЕНТА:\n{student_text}")

    # For CODE type — add test results if available
    if question_type == 'CODE':
        test_results = student.get('test_results')
        if test_results:
            prompt_parts.append(f"\nРЕЗУЛЬТАТЫ ТЕСТОВ:\n{json.dumps(test_results, ensure_ascii=False, indent=2)}")
        language = student.get('language', '')
        if language:
            prompt_parts.append(f"\nЯЗЫК ПРОГРАММИРОВАНИЯ: {language}")

    # For FILE_UPLOAD — add file metadata
    if question_type == 'FILE_UPLOAD':
        file_info = student.get('file_info')
        if file_info:
            prompt_parts.append(f"\nИНФОРМАЦИЯ О ФАЙЛЕ:\n{json.dumps(file_info, ensure_ascii=False)}")

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': '\n'.join(prompt_parts)},
    ]

    # Call AI with provider failover
    provider_chain = settings.AI_GRADING_PROVIDER_CHAIN
    # Override with homework-specific provider if set
    hw_provider = config.get('provider')
    if hw_provider and hw_provider != 'deepseek':
        provider_chain = [{'provider': hw_provider, 'model': None}] + provider_chain

    last_error = None
    start_time = time.time()

    for provider_config in provider_chain:
        provider = provider_config['provider']
        model = provider_config.get('model')

        try:
            raw_response = _call_ai_provider(
                provider=provider,
                model=model,
                messages=messages,
                timeout=settings.AI_GRADING_TIMEOUT,
            )

            # Parse response
            elapsed_ms = int((time.time() - start_time) * 1000)
            result = _parse_ai_response(raw_response, question.get('max_points', 10))

            # Calculate cost
            usage = raw_response.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            cost = _calculate_cost(provider, model, input_tokens, output_tokens)

            # Record success
            _record_circuit_success()

            # Send success callback
            callback_payload = {
                'task_id': task_id,
                'status': 'completed',
                'completed_at': _now_iso(),
                'result': {
                    'answer_id': answer_id,
                    'score': result['score'],
                    'max_points': question.get('max_points', 10),
                    'confidence': result['confidence'],
                    'feedback': result['feedback'],
                    'review': result.get('review'),  # Структурированный ревью
                    'needs_manual_review': result['confidence'] < 0.7,
                    'ai_metadata': {
                        'provider': provider,
                        'model': model or 'unknown',
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'cost_rubles': float(cost),
                        'latency_ms': elapsed_ms,
                        'prompt_version': 'v2',
                    },
                },
            }

            _send_callback(callback_url, callback_payload)

            logger.info(
                f"AI grading done: answer={answer_id}, score={result['score']}, "
                f"confidence={result['confidence']:.0%}, provider={provider}, "
                f"latency={elapsed_ms}ms, cost={cost}RUB"
            )
            return  # Success!

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            last_error = f"{provider}: HTTP {status_code}"
            logger.warning(f"AI provider {provider} error: HTTP {status_code}")

            if status_code in (400, 401, 403):
                # Bad request — don't retry with same provider
                continue
            if status_code in (429, 500, 502, 503, 504):
                _record_circuit_failure()
                continue

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = f"{provider}: {type(e).__name__}"
            logger.warning(f"AI provider {provider} connection error: {e}")
            _record_circuit_failure()
            continue

        except Exception as e:
            last_error = f"{provider}: {type(e).__name__}: {e}"
            logger.exception(f"AI provider {provider} unexpected error")
            continue

    # All providers failed — retry or DLQ
    retry_count = self.request.retries
    if retry_count < self.max_retries:
        delay = 2 ** (retry_count + 1)  # Exponential: 2, 4, 8 sec
        logger.warning(
            f"AI grading retry {retry_count + 1}/{self.max_retries}: "
            f"answer={answer_id}, delay={delay}s, error={last_error}"
        )
        raise self.retry(countdown=delay)

    # Exhausted retries → send failure callback
    logger.error(
        f"AI grading FAILED after {self.max_retries} retries: "
        f"answer={answer_id}, error={last_error}"
    )
    _send_failure_callback(
        callback_url, task_id, answer_id,
        'PROVIDER_UNAVAILABLE',
        f'All providers failed after {self.max_retries} retries. Last error: {last_error}',
        retries=self.max_retries,
    )


@shared_task(
    name='homework.tasks.process_ai_grading_dlq',
    soft_time_limit=120,
    time_limit=180,
)
def process_ai_grading_dlq(payload: dict):
    """
    Dead Letter Queue processor — retry failed AI grading tasks.
    Can be triggered manually by admin.
    """
    logger.info(f"DLQ processing: task={payload.get('task_id')}")
    # Re-enqueue to main queue
    process_ai_grading.apply_async(
        args=[payload],
        queue='ai_grading',
    )


def _parse_ai_response(raw_response: dict, max_points: int) -> dict:
    """Parse AI response JSON from chat completion — structured review format."""
    try:
        content = raw_response['choices'][0]['message']['content']
        # Try to parse as JSON
        content = content.strip()
        if content.startswith('```'):
            # Strip markdown code fences
            content = content.split('\n', 1)[1] if '\n' in content else content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()

        result = json.loads(content)
        score = int(result.get('score', 0))
        score = max(0, min(score, max_points))

        # Parse structured review
        criteria = result.get('criteria', [])
        # Validate each criterion
        validated_criteria = []
        for c in criteria:
            validated_criteria.append({
                'name': str(c.get('name', '')),
                'score': max(0, int(c.get('score', 0))),
                'max_score': max(1, int(c.get('max_score', 1))),
                'comment': str(c.get('comment', '')),
            })

        review = {
            'criteria': validated_criteria,
            'strengths': [str(s) for s in result.get('strengths', [])],
            'weaknesses': [str(w) for w in result.get('weaknesses', [])],
            'recommendations': [str(r) for r in result.get('recommendations', [])],
            'summary': str(result.get('summary', result.get('feedback', ''))),
        }

        return {
            'score': score,
            'feedback': review['summary'],
            'confidence': float(result.get('confidence', 0.5)),
            'review': review,
        }
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        logger.warning(f"Failed to parse AI response: {e}")
        return {
            'score': 0,
            'feedback': 'AI не смог оценить ответ (ошибка парсинга)',
            'confidence': 0.0,
            'review': None,
        }


def _calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Calculate cost in rubles."""
    COSTS = {
        'deepseek-chat': {'input': 1.33, 'output': 2.66},
        'deepseek-reasoner': {'input': 5.32, 'output': 19.95},
        'gpt-4o-mini': {'input': 14.25, 'output': 57.0},
    }
    rates = COSTS.get(model or '', COSTS.get('deepseek-chat'))
    cost = (input_tokens / 1_000_000) * rates['input'] + (output_tokens / 1_000_000) * rates['output']
    return Decimal(str(round(cost, 6)))


def _send_failure_callback(callback_url, task_id, answer_id, error_code, message, retries=0):
    """Send failure callback to Django."""
    payload = {
        'task_id': task_id,
        'status': 'failed',
        'completed_at': _now_iso(),
        'error': {
            'code': error_code,
            'message': message,
            'retries_attempted': retries,
        },
        'fallback': {
            'answer_id': answer_id,
            'needs_manual_review': True,
            'feedback': f'[AI недоступен: {error_code}] Требуется ручная проверка',
        },
    }
    _send_callback(callback_url, payload)


def _now_iso() -> str:
    """Current UTC time as ISO string."""
    from django.utils import timezone
    return timezone.now().isoformat()
