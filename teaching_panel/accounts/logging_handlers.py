import hashlib
import logging
import os
import traceback
import threading
from datetime import timedelta

from django.apps import apps
from django.db import OperationalError
from django.utils import timezone


class DatabaseErrorLogHandler(logging.Handler):
    """Пишет ERROR/CRITICAL логи в таблицу SystemErrorEvent.

    Безопасен: любые ошибки внутри handler подавляются, чтобы не зациклить логирование.
    Thread-safe: использует RLock для предотвращения reentrant ошибок.
    """
    
    # Глобальный lock для предотвращения reentrant вызовов
    _emit_lock = threading.RLock()

    def emit(self, record: logging.LogRecord) -> None:
        # Используем non-blocking tryLock чтобы избежать deadlock
        acquired = self._emit_lock.acquire(blocking=False)
        if not acquired:
            # Другой поток уже пишет, пропускаем
            return
        
        try:
            self._do_emit(record)
        finally:
            self._emit_lock.release()
    
    def _do_emit(self, record: logging.LogRecord) -> None:
        """Реальная логика emit, защищённая lock'ом."""
        try:
            if os.environ.get('DB_ERROR_LOGGING', '1') != '1':
                return

            SystemErrorEvent = apps.get_model('accounts', 'SystemErrorEvent')

            now = timezone.now()

            severity = self._map_severity(record)
            source = (getattr(record, 'error_source', None) or record.name or 'backend')[:80]
            code = (getattr(record, 'error_code', None) or self._extract_code(record))[:80]

            teacher = self._get_teacher(record)

            message = self.format(record)
            if not message:
                message = str(getattr(record, 'msg', ''))

            details = self._build_details(record)

            fingerprint = self._fingerprint(
                severity=severity,
                source=source,
                code=code,
                teacher_id=getattr(teacher, 'id', None),
                message=message,
            )

            request_path = (getattr(record, 'request_path', None) or '')[:300]
            request_method = (getattr(record, 'request_method', None) or '')[:10]

            req = getattr(record, 'request', None)
            if req is not None:
                try:
                    if not request_path:
                        request_path = (getattr(req, 'path', '') or '')[:300]
                    if not request_method:
                        request_method = (getattr(req, 'method', '') or '')[:10]
                except Exception:
                    pass
            process = (getattr(record, 'process_name', None) or '')[:80]

            dedupe_window = timedelta(minutes=int(os.environ.get('DB_ERROR_DEDUPE_MINUTES', '60')))

            try:
                existing = (
                    SystemErrorEvent.objects
                    .filter(fingerprint=fingerprint, resolved_at__isnull=True, last_seen_at__gte=now - dedupe_window)
                    .order_by('-last_seen_at')
                    .first()
                )
            except OperationalError:
                return

            if existing:
                existing.occurrences = (existing.occurrences or 1) + 1
                existing.last_seen_at = now
                if details:
                    existing.details = details
                if request_path:
                    existing.request_path = request_path
                if request_method:
                    existing.request_method = request_method
                if process:
                    existing.process = process
                existing.save(update_fields=['occurrences', 'last_seen_at', 'details', 'request_path', 'request_method', 'process'])
                return

            SystemErrorEvent.objects.create(
                severity=severity,
                source=source,
                code=code,
                message=message,
                details=details,
                teacher=teacher,
                request_path=request_path,
                request_method=request_method,
                process=process,
                fingerprint=fingerprint,
                occurrences=1,
                last_seen_at=now,
            )
        except Exception:
            # Никогда не даём handler-у падать.
            return

    def _map_severity(self, record: logging.LogRecord) -> str:
        level = int(getattr(record, 'levelno', logging.ERROR))
        if level >= logging.CRITICAL:
            return 'critical'
        if level >= logging.ERROR:
            return 'error'
        return 'warning'

    def _extract_code(self, record: logging.LogRecord) -> str:
        if record.exc_info and record.exc_info[0]:
            return getattr(record.exc_info[0], '__name__', 'Exception')
        return 'LOG_ERROR'

    def _build_details(self, record: logging.LogRecord) -> dict:
        details: dict = {}

        if record.exc_info:
            details['exception_type'] = getattr(record.exc_info[0], '__name__', 'Exception') if record.exc_info[0] else 'Exception'
            details['exception_message'] = str(record.exc_info[1]) if record.exc_info[1] else ''
            details['traceback'] = ''.join(traceback.format_exception(*record.exc_info))[-20000:]

        # Пробрасываем пользовательский контекст, если его передали.
        extra_details = getattr(record, 'details', None)
        if isinstance(extra_details, dict) and extra_details:
            details.update(extra_details)

        return details

    def _get_teacher(self, record: logging.LogRecord):
        try:
            teacher_id = getattr(record, 'teacher_id', None)

            req = getattr(record, 'request', None)
            if not teacher_id and req is not None:
                user = getattr(req, 'user', None)
                if user is not None and getattr(user, 'is_authenticated', False) and getattr(user, 'role', '') == 'teacher':
                    teacher_id = getattr(user, 'id', None)

            if not teacher_id:
                return None

            UserModel = apps.get_model('accounts', 'CustomUser')
            return UserModel.objects.filter(id=teacher_id, role='teacher').first()
        except Exception:
            return None

    def _fingerprint(self, *, severity: str, source: str, code: str, teacher_id, message: str) -> str:
        base = f"{severity}|{source}|{code}|{teacher_id or ''}|{(message or '')[:500]}"
        return hashlib.sha256(base.encode('utf-8')).hexdigest()[:64]
