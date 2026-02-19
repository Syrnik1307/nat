import logging
from typing import Any
import uuid

import requests
from django.conf import settings
from django.core.mail import mail_admins
from django.utils import timezone


logger = logging.getLogger(__name__)


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    return [str(value).strip()]


def _build_payload(session, incident_type: str, reason: str, severity: str, metadata: dict | None = None) -> dict:
    content = getattr(session, 'content', None)
    lesson = getattr(content, 'lesson', None) if content else None
    course = getattr(lesson, 'course', None) if lesson else None
    user = getattr(session, 'user', None)
    tenant = getattr(session, 'tenant', None)

    return {
        'source': 'content-protection',
        'event': incident_type,
        'severity': severity,
        'reason': reason,
        'timestamp': timezone.now().isoformat(),
        'session': {
            'token': str(getattr(session, 'session_token', '')),
            'status': getattr(session, 'status', ''),
            'risk_score': getattr(session, 'risk_score', 0),
            'blocked_reason': getattr(session, 'block_reason', ''),
        },
        'tenant': {
            'id': getattr(tenant, 'id', None),
            'slug': getattr(tenant, 'slug', ''),
            'name': getattr(tenant, 'name', ''),
        },
        'user': {
            'id': getattr(user, 'id', None),
            'email': getattr(user, 'email', ''),
            'role': getattr(user, 'role', ''),
        },
        'content': {
            'id': getattr(content, 'id', None),
            'title': getattr(content, 'title', ''),
            'lesson_id': getattr(lesson, 'id', None),
            'lesson_title': getattr(lesson, 'title', ''),
            'course_id': getattr(course, 'id', None),
            'course_title': getattr(course, 'title', ''),
        },
        'metadata': metadata or {},
    }


def _send_webhook(payload: dict) -> None:
    webhook_url = getattr(settings, 'CONTENT_PROTECTION_ALERT_WEBHOOK_URL', '').strip()
    if not webhook_url:
        return

    timeout = int(getattr(settings, 'CONTENT_PROTECTION_ALERT_TIMEOUT_SECONDS', 5))
    token = getattr(settings, 'CONTENT_PROTECTION_ALERT_WEBHOOK_TOKEN', '').strip()
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    requests.post(webhook_url, json=payload, headers=headers, timeout=timeout)


def _send_email(payload: dict) -> None:
    if not getattr(settings, 'CONTENT_PROTECTION_ALERT_EMAIL_ENABLED', False):
        return

    subject = f"[ContentProtection][{payload['severity']}] {payload['event']}"
    lines = [
        f"Причина: {payload['reason']}",
        f"Пользователь: {payload['user'].get('email')} (id={payload['user'].get('id')})",
        f"Тенант: {payload['tenant'].get('slug')} ({payload['tenant'].get('name')})",
        f"Курс/урок: {payload['content'].get('course_title')} / {payload['content'].get('lesson_title')}",
        f"Сессия: {payload['session'].get('token')}",
        f"Risk score: {payload['session'].get('risk_score')}",
        f"Blocked reason: {payload['session'].get('blocked_reason')}",
        f"Metadata: {payload.get('metadata', {})}",
    ]
    message = '\n'.join(lines)
    mail_admins(subject, message, fail_silently=True)


def _send_telegram(payload: dict) -> None:
    if not getattr(settings, 'CONTENT_PROTECTION_ALERT_TELEGRAM_ENABLED', False):
        return

    bot_token = getattr(settings, 'CONTENT_PROTECTION_ALERT_TELEGRAM_BOT_TOKEN', '').strip()
    chat_ids = _as_list(getattr(settings, 'CONTENT_PROTECTION_ALERT_TELEGRAM_CHAT_IDS', []))
    if not bot_token or not chat_ids:
        return

    timeout = int(getattr(settings, 'CONTENT_PROTECTION_ALERT_TIMEOUT_SECONDS', 5))
    text = (
        f"🚨 Content protection incident\n"
        f"severity={payload['severity']} event={payload['event']}\n"
        f"tenant={payload['tenant'].get('slug')} user={payload['user'].get('email')}\n"
        f"course={payload['content'].get('course_title')} lesson={payload['content'].get('lesson_title')}\n"
        f"reason={payload['reason']}\n"
        f"risk={payload['session'].get('risk_score')}"
    )

    for chat_id in chat_ids:
        try:
            requests.post(
                f'https://api.telegram.org/bot{bot_token}/sendMessage',
                json={'chat_id': chat_id, 'text': text},
                timeout=timeout,
            )
        except Exception:
            logger.exception('Failed to send content protection alert to telegram chat_id=%s', chat_id)


def _send_vk(payload: dict) -> None:
    if not getattr(settings, 'CONTENT_PROTECTION_ALERT_VK_ENABLED', False):
        return

    access_token = getattr(settings, 'CONTENT_PROTECTION_ALERT_VK_ACCESS_TOKEN', '').strip()
    api_version = getattr(settings, 'CONTENT_PROTECTION_ALERT_VK_API_VERSION', '5.199').strip() or '5.199'
    peer_ids = _as_list(getattr(settings, 'CONTENT_PROTECTION_ALERT_VK_PEER_IDS', []))
    user_ids = _as_list(getattr(settings, 'CONTENT_PROTECTION_ALERT_VK_USER_IDS', []))

    targets: list[tuple[str, str]] = []
    targets.extend([('peer_id', value) for value in peer_ids])
    targets.extend([('user_id', value) for value in user_ids])

    if not access_token or not targets:
        return

    timeout = int(getattr(settings, 'CONTENT_PROTECTION_ALERT_TIMEOUT_SECONDS', 5))
    text = (
        f"🚨 Инцидент защиты контента\n"
        f"Уровень: {payload['severity']}\n"
        f"Событие: {payload['event']}\n"
        f"Тенант: {payload['tenant'].get('slug')}\n"
        f"Пользователь: {payload['user'].get('email')}\n"
        f"Курс: {payload['content'].get('course_title')}\n"
        f"Урок: {payload['content'].get('lesson_title')}\n"
        f"Причина: {payload['reason']}\n"
        f"Risk score: {payload['session'].get('risk_score')}"
    )

    for target_field, target_value in targets:
        try:
            params = {
                'access_token': access_token,
                'v': api_version,
                'random_id': str(uuid.uuid4().int % (2**31 - 1)),
                'message': text,
                target_field: target_value,
            }
            requests.post('https://api.vk.com/method/messages.send', data=params, timeout=timeout)
        except Exception:
            logger.exception('Failed to send content protection alert to VK %s=%s', target_field, target_value)


def notify_content_security_incident(
    session,
    incident_type: str,
    reason: str,
    severity: str = 'warning',
    metadata: dict | None = None,
) -> None:
    payload = _build_payload(
        session=session,
        incident_type=incident_type,
        reason=reason,
        severity=severity,
        metadata=metadata,
    )

    try:
        _send_webhook(payload)
    except Exception:
        logger.exception('Failed to send content protection alert via webhook')

    try:
        _send_email(payload)
    except Exception:
        logger.exception('Failed to send content protection alert via email')

    try:
        _send_telegram(payload)
    except Exception:
        logger.exception('Failed to send content protection alert via telegram')

    try:
        _send_vk(payload)
    except Exception:
        logger.exception('Failed to send content protection alert via vk')
