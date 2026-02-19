"""
AI Grading Service — проверка текстовых ответов через AI.

Поддерживаемые провайдеры:
  - gemini  (Google Gemini API)
  - deepseek (DeepSeek chat API)
  - openai  (OpenAI ChatCompletion API)
"""

import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ─── system prompt (общий для всех провайдеров) ──────────────────────────────
SYSTEM_PROMPT = """Ты — опытный школьный учитель. Твоя задача — проверить ответ ученика на вопрос домашнего задания.

Инструкции:
1. Оцени ответ ученика по шкале от 0 до {max_points} баллов.
2. Учти правильность, полноту, грамотность и логику ответа.
3. Напиши краткий комментарий к оценке (2-4 предложения).
4. Ответь СТРОГО в формате JSON без обрамления в ```json ... ```:

{{"score": <число от 0 до {max_points}>, "feedback": "<комментарий учителя>"}}

Больше ничего не пиши, только JSON."""

USER_PROMPT_TEMPLATE = """Вопрос: {question}

Ответ ученика: {answer}

Максимальный балл: {max_points}
{extra_instructions}"""


def _build_prompts(question_text: str, answer_text: str, max_points: int, extra_instructions: str = ""):
    """Формирует system + user промпты."""
    system = SYSTEM_PROMPT.format(max_points=max_points)
    extra = f"\nДополнительные критерии оценки: {extra_instructions}" if extra_instructions else ""
    user = USER_PROMPT_TEMPLATE.format(
        question=question_text,
        answer=answer_text,
        max_points=max_points,
        extra_instructions=extra,
    )
    return system, user


def _parse_ai_response(raw_text: str, max_points: int):
    """Извлекает score и feedback из ответа AI."""
    text = raw_text.strip()
    # Убираем markdown code-fence, если AI всё-таки обернул
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("AI returned non-JSON: %s", text[:300])
        return None, f"[AI не смог дать оценку. Ответ AI: {text[:200]}]"

    score = data.get("score")
    feedback = data.get("feedback", "")

    if score is None:
        return None, feedback or "[AI не вернул оценку]"

    # Clamp
    score = max(0, min(int(score), max_points))
    return score, feedback


# ═══════════════════════════════════════════════════════════════════════════════
# ПРОВАЙДЕРЫ
# ═══════════════════════════════════════════════════════════════════════════════

def _call_gemini(system: str, user: str) -> str:
    """Вызов Google Gemini API (REST, без SDK)."""
    api_key = settings.GEMINI_API_KEY
    model = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash-lite')

    if not api_key:
        raise ValueError("GEMINI_API_KEY не настроен в settings / .env")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system}\n\n{user}"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        }
    }

    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # Извлекаем текст из ответа
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        logger.error("Gemini unexpected response: %s", json.dumps(data, ensure_ascii=False)[:500])
        raise ValueError(f"Gemini вернул неожиданный формат: {exc}") from exc


def _call_deepseek(system: str, user: str) -> str:
    """Вызов DeepSeek Chat API."""
    api_key = settings.DEEPSEEK_API_KEY
    api_url = getattr(settings, 'DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
    model = getattr(settings, 'DEEPSEEK_MODEL', 'deepseek-chat')

    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY не настроен в settings / .env")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_openai(system: str, user: str) -> str:
    """Вызов OpenAI ChatCompletion API."""
    api_key = settings.OPENAI_API_KEY
    model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

    if not api_key:
        raise ValueError("OPENAI_API_KEY не настроен в settings / .env")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    resp = requests.post("https://api.openai.com/v1/chat/completions",
                         headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


PROVIDER_MAP = {
    "gemini": _call_gemini,
    "deepseek": _call_deepseek,
    "openai": _call_openai,
}


# ═══════════════════════════════════════════════════════════════════════════════
# ПУБЛИЧНЫЙ API
# ═══════════════════════════════════════════════════════════════════════════════

def grade_answer_with_ai(
    provider: str,
    question_text: str,
    answer_text: str,
    max_points: int,
    extra_instructions: str = "",
) -> dict:
    """
    Проверяет текстовый ответ ученика через AI.

    Возвращает dict:
        {"score": int | None, "feedback": str, "error": str | None}
    """
    if provider not in PROVIDER_MAP:
        return {"score": None, "feedback": "", "error": f"Неизвестный AI-провайдер: {provider}"}

    system, user = _build_prompts(question_text, answer_text, max_points, extra_instructions)
    call_fn = PROVIDER_MAP[provider]

    try:
        raw = call_fn(system, user)
        logger.info("AI (%s) raw response: %s", provider, raw[:300])
        score, feedback = _parse_ai_response(raw, max_points)
        return {"score": score, "feedback": feedback, "error": None}
    except Exception as exc:
        logger.exception("AI grading failed (%s)", provider)
        return {"score": None, "feedback": "", "error": str(exc)}


def check_provider_health(provider: str) -> dict:
    """
    Проверяет работоспособность AI-провайдера простым тестовым запросом.

    Возвращает: {"ok": bool, "message": str, "raw_response": str}
    """
    if provider not in PROVIDER_MAP:
        return {"ok": False, "message": f"Неизвестный провайдер: {provider}", "raw_response": ""}

    system = "Ты — помощник. Ответь одним словом."
    user = "Сколько будет 2 + 2? Ответь только числом."

    call_fn = PROVIDER_MAP[provider]
    try:
        raw = call_fn(system, user)
        return {"ok": True, "message": f"Провайдер {provider} работает", "raw_response": raw.strip()}
    except Exception as exc:
        return {"ok": False, "message": str(exc), "raw_response": ""}
