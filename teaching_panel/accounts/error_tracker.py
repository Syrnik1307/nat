"""
Централизованный трекинг ошибок для admin-панели.

Использование:
    from accounts.error_tracker import track_error

    # Простой вызов
    track_error('HW_UPLOAD_FAILED', 'Не удалось загрузить ДЗ', teacher=request.user)

    # С деталями
    track_error(
        'ZOOM_CREATE_FAILED',
        'Ошибка создания Zoom встречи',
        severity='critical',
        teacher=teacher,
        details={'lesson_id': 123, 'zoom_error': str(e)},
        exc=e,
    )

Severity levels:
    - 'critical': Критические ошибки (платежи, потеря данных, Zoom не работает)
    - 'error': Важные ошибки (загрузка ДЗ, записи, уведомления)
    - 'warning': Некритичные (валидация, мелкие сбои)
"""
import hashlib
import logging
import traceback
from typing import Any, Dict, Optional

from django.apps import apps
from django.db import OperationalError
from django.utils import timezone

logger = logging.getLogger('error_tracker')


def track_error(
    code: str,
    message: str,
    *,
    severity: str = 'error',
    source: str = 'backend',
    teacher=None,
    student=None,
    request=None,
    details: Optional[Dict[str, Any]] = None,
    exc: Optional[BaseException] = None,
    process: str = '',
    dedupe_minutes: int = 60,
) -> bool:
    """
    Записывает ошибку в SystemErrorEvent для отображения в админ-панели.

    Args:
        code: Уникальный код ошибки (например: HW_UPLOAD_FAILED, ZOOM_CREATE_FAILED)
        message: Человекочитаемое описание ошибки
        severity: 'critical' | 'error' | 'warning'
        source: Источник ошибки (модуль/сервис)
        teacher: Объект учителя (CustomUser) или его ID
        student: Объект студента (для привязки к учителю через группу)
        request: Django request для автоматического извлечения пути и учителя
        details: Словарь с дополнительными данными
        exc: Исключение для извлечения traceback
        process: Название процесса (celery task, webhook и т.д.)
        dedupe_minutes: Окно дедупликации (по умолчанию 60 минут)

    Returns:
        True если ошибка записана, False если пропущена (дубликат или ошибка записи)
    """
    try:
        SystemErrorEvent = apps.get_model('accounts', 'SystemErrorEvent')
        CustomUser = apps.get_model('accounts', 'CustomUser')

        now = timezone.now()

        # Normalize severity
        severity = severity.lower()
        if severity not in ('critical', 'error', 'warning'):
            severity = 'error'

        # Resolve teacher
        teacher_obj = None
        teacher_id = None

        if teacher is not None:
            if isinstance(teacher, int):
                teacher_id = teacher
            elif hasattr(teacher, 'id'):
                teacher_id = teacher.id
                teacher_obj = teacher if getattr(teacher, 'role', '') == 'teacher' else None

        # Try to get teacher from request
        if teacher_id is None and request is not None:
            user = getattr(request, 'user', None)
            if user is not None and getattr(user, 'is_authenticated', False):
                if getattr(user, 'role', '') == 'teacher':
                    teacher_id = user.id
                    teacher_obj = user

        # Try to get teacher from student (через группы)
        if teacher_id is None and student is not None:
            try:
                student_id = student.id if hasattr(student, 'id') else student
                student_obj = CustomUser.objects.filter(id=student_id, role='student').first()
                if student_obj:
                    # Берём первого учителя из групп студента
                    Group = apps.get_model('schedule', 'Group')
                    group = Group.objects.filter(students=student_obj).select_related('teacher').first()
                    if group and group.teacher:
                        teacher_id = group.teacher.id
                        teacher_obj = group.teacher
            except Exception:
                pass

        # Load teacher object if we only have ID
        if teacher_id and teacher_obj is None:
            try:
                teacher_obj = CustomUser.objects.filter(id=teacher_id, role='teacher').first()
            except Exception:
                pass

        # Build details
        full_details: Dict[str, Any] = {}
        if details:
            full_details.update(details)

        if exc is not None:
            full_details['exception_type'] = exc.__class__.__name__
            full_details['exception_message'] = str(exc)[:1000]
            tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            full_details['traceback'] = tb[-15000:]

        if student is not None:
            student_id = student.id if hasattr(student, 'id') else student
            full_details['student_id'] = student_id

        # Extract request info
        request_path = ''
        request_method = ''
        if request is not None:
            try:
                request_path = (getattr(request, 'path', '') or '')[:300]
                request_method = (getattr(request, 'method', '') or '')[:10]
            except Exception:
                pass

        # Fingerprint for deduplication
        fingerprint = _fingerprint(
            severity=severity,
            source=source[:80],
            code=code[:80],
            teacher_id=teacher_id,
            message=message[:500],
        )

        # Check for existing (dedupe)
        from datetime import timedelta
        dedupe_window = timedelta(minutes=max(1, dedupe_minutes))

        try:
            existing = (
                SystemErrorEvent.objects
                .filter(fingerprint=fingerprint, resolved_at__isnull=True, last_seen_at__gte=now - dedupe_window)
                .order_by('-last_seen_at')
                .first()
            )
        except OperationalError:
            logger.warning('DB not ready for error tracking')
            return False

        if existing:
            existing.occurrences = (existing.occurrences or 1) + 1
            existing.last_seen_at = now
            if full_details:
                existing.details = full_details
            if request_path:
                existing.request_path = request_path
            if request_method:
                existing.request_method = request_method
            if process:
                existing.process = process[:80]
            existing.save(update_fields=['occurrences', 'last_seen_at', 'details', 'request_path', 'request_method', 'process'])
            return False  # Deduplicated

        SystemErrorEvent.objects.create(
            severity=severity,
            source=source[:80],
            code=code[:80],
            message=message[:2000],
            details=full_details,
            teacher=teacher_obj,
            request_path=request_path,
            request_method=request_method,
            process=process[:80],
            fingerprint=fingerprint,
            occurrences=1,
            last_seen_at=now,
        )

        # Also log to standard logger
        log_level = logging.CRITICAL if severity == 'critical' else logging.ERROR if severity == 'error' else logging.WARNING
        logger.log(log_level, f"[{code}] {message}", extra={'teacher_id': teacher_id, 'details': full_details})

        return True

    except Exception as e:
        # Never crash - just log to stderr
        logger.exception(f'Error in track_error: {e}')
        return False


def _fingerprint(*, severity: str, source: str, code: str, teacher_id, message: str) -> str:
    base = f"{severity}|{source}|{code}|{teacher_id or ''}|{(message or '')[:500]}"
    return hashlib.sha256(base.encode('utf-8')).hexdigest()[:64]


# Convenience functions for common error types
def track_critical(code: str, message: str, **kwargs):
    """Критическая ошибка (платежи, потеря данных)"""
    return track_error(code, message, severity='critical', **kwargs)


def track_warning(code: str, message: str, **kwargs):
    """Некритичная ошибка (валидация, мелкие сбои)"""
    return track_error(code, message, severity='warning', **kwargs)
