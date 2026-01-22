import hashlib
import json
import logging
import os
import traceback
from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessEvent:
    event_type: str
    severity: str
    occurred_at: datetime
    teacher_id: Optional[int] = None
    teacher_email: str = ''
    actor_user_id: Optional[int] = None
    actor_email: str = ''
    actor_role: str = ''
    context: Optional[Dict[str, Any]] = None
    error_class: str = ''
    error_message: str = ''
    error_hash: str = ''


def _get_process_alerts_config() -> tuple[str, str]:
    token = getattr(settings, 'PROCESS_ALERTS_BOT_TOKEN', '') or os.environ.get('PROCESS_ALERTS_BOT_TOKEN', '')
    chat_id = getattr(settings, 'PROCESS_ALERTS_CHAT_ID', '') or os.environ.get('PROCESS_ALERTS_CHAT_ID', '')

    # Optional fallback to monitoring vars (if they are present in the service env)
    token = token or os.environ.get('ERRORS_BOT_TOKEN', '')
    chat_id = chat_id or os.environ.get('ERRORS_CHAT_ID', '')

    return (token or '').strip(), (chat_id or '').strip()


def _stable_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _dedupe_key(event_type: str, severity: str, teacher_id: Optional[int], actor_user_id: Optional[int], error_hash: str) -> str:
    base = {
        'event_type': event_type,
        'severity': severity,
        'teacher_id': teacher_id,
        'actor_user_id': actor_user_id,
        'error_hash': error_hash,
    }
    digest = _stable_hash(base)[:24]
    return f'process_event_dedupe:{digest}'


def _format_telegram_message(evt: ProcessEvent) -> str:
    lines = [
        f"<b>PROCESS</b>: {escape(evt.event_type)}",
        f"Severity: {escape(evt.severity)}",
    ]

    if evt.teacher_id or evt.teacher_email:
        lines.append(f"Teacher: {escape(str(evt.teacher_id or ''))} {escape(evt.teacher_email)}".strip())

    if evt.actor_user_id or evt.actor_email:
        actor_bits = [
            str(evt.actor_user_id or ''),
            evt.actor_email or '',
            evt.actor_role or '',
        ]
        actor_bits = [b for b in actor_bits if b]
        lines.append(f"Actor: {escape(' '.join(actor_bits))}")

    if evt.error_class or evt.error_message:
        err = f"{evt.error_class}: {evt.error_message}".strip(': ')
        if err:
            lines.append(f"Error: {escape(err[:350])}")

    if evt.error_hash:
        lines.append(f"ErrorHash: {escape(evt.error_hash[:12])}")

    ctx = evt.context or {}
    if ctx:
        # Keep short: no huge dumps
        safe_ctx: Dict[str, Any] = {}
        for k, v in ctx.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                safe_ctx[k] = v
            else:
                safe_ctx[k] = str(v)

        if safe_ctx:
            ctx_json = json.dumps(safe_ctx, ensure_ascii=False, sort_keys=True, default=str)
            lines.append(f"Context: <code>{escape(ctx_json[:600])}</code>")

    ts = timezone.localtime(evt.occurred_at).strftime('%Y-%m-%d %H:%M:%S')
    lines.append(f"At: {escape(ts)}")

    return "\n".join(lines)


def emit_process_event(
    *,
    event_type: str,
    severity: str = 'error',
    actor_user=None,
    teacher=None,
    context: Optional[Dict[str, Any]] = None,
    exc: Optional[BaseException] = None,
    dedupe_seconds: int = 600,
) -> bool:
    """Emit a process/incident event.

    - Always logs to app logger.
    - Optionally sends a short Telegram alert if PROCESS_ALERTS_* configured.
    - Uses cache-based dedupe to avoid spam.

    This must never raise.
    """
    try:
        occurred_at = timezone.now()

        teacher_id = getattr(teacher, 'id', None) if teacher is not None else None
        teacher_email = (getattr(teacher, 'email', '') or '') if teacher is not None else ''

        actor_user_id = getattr(actor_user, 'id', None) if actor_user is not None else None
        actor_email = (getattr(actor_user, 'email', '') or '') if actor_user is not None else ''
        actor_role = (getattr(actor_user, 'role', '') or '') if actor_user is not None else ''

        error_class = ''
        error_message = ''
        error_hash = ''

        if exc is not None:
            error_class = exc.__class__.__name__
            error_message = str(exc)[:500]
            tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            error_hash = hashlib.sha1(tb.encode('utf-8', errors='ignore')).hexdigest()

        evt = ProcessEvent(
            event_type=event_type,
            severity=severity,
            occurred_at=occurred_at,
            teacher_id=teacher_id,
            teacher_email=teacher_email,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            actor_role=actor_role,
            context=context or {},
            error_class=error_class,
            error_message=error_message,
            error_hash=error_hash,
        )

        # Dedupe
        key = _dedupe_key(event_type, severity, teacher_id, actor_user_id, error_hash)
        if cache.get(key):
            logger.info('process_event_deduped %s', {
                'event_type': event_type,
                'severity': severity,
                'teacher_id': teacher_id,
                'actor_user_id': actor_user_id,
                'error_hash': error_hash[:12],
            })
            return False
        cache.set(key, True, timeout=max(30, int(dedupe_seconds)))

        logger.warning('process_event %s', {
            'event_type': evt.event_type,
            'severity': evt.severity,
            'teacher_id': evt.teacher_id,
            'teacher_email': evt.teacher_email,
            'actor_user_id': evt.actor_user_id,
            'actor_email': evt.actor_email,
            'actor_role': evt.actor_role,
            'context': evt.context,
            'error_class': evt.error_class,
            'error_message': evt.error_message,
            'error_hash': evt.error_hash[:12],
        })

        token, chat_id = _get_process_alerts_config()
        if not token or not chat_id:
            return True

        message = _format_telegram_message(evt)
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        }

        try:
            resp = requests.post(url, json=payload, timeout=8)
            if not resp.ok:
                logger.warning('process_event_telegram_failed %s %s', resp.status_code, resp.text[:500])
            return True
        except Exception as send_exc:
            logger.warning('process_event_telegram_exception %s', send_exc)
            return True

    except Exception:
        logger.exception('emit_process_event failed')
        return False
