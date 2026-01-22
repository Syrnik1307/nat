from django.core.cache import cache
from datetime import timedelta
from django.utils import timezone

LOCKOUT_THRESHOLD = 5  # попыток
LOCKOUT_MINUTES = 10
FAIL_PREFIX = 'login_fail:'
LOCK_PREFIX = 'login_lock:'


def _fail_key(email: str) -> str:
    return f"{FAIL_PREFIX}{email.lower()}"


def _lock_key(email: str) -> str:
    return f"{LOCK_PREFIX}{email.lower()}"


def is_locked(email: str) -> bool:
    return cache.get(_lock_key(email)) is not None


def register_failure(email: str) -> None:
    key = _fail_key(email)
    fails = cache.get(key, 0) + 1
    cache.set(key, fails, LOCKOUT_MINUTES * 60)
    if fails >= LOCKOUT_THRESHOLD:
        cache.set(_lock_key(email), True, LOCKOUT_MINUTES * 60)

        # Best-effort process alert only on threshold hit (avoid spam)
        if fails == LOCKOUT_THRESHOLD:
            try:
                from django.contrib.auth import get_user_model
                from teaching_panel.observability.process_events import emit_process_event

                User = get_user_model()
                user = None
                try:
                    user = User.objects.filter(email__iexact=email).first()
                except Exception:
                    user = None

                teacher = user if user and getattr(user, 'role', None) == 'teacher' else None

                emit_process_event(
                    event_type='login_account_locked',
                    severity='warning',
                    actor_user=user,
                    teacher=teacher,
                    context={
                        'email': email,
                        'fails': fails,
                        'lockout_minutes': LOCKOUT_MINUTES,
                    },
                    dedupe_seconds=3600,
                )
            except Exception:
                pass


def reset_failures(email: str) -> None:
    cache.delete_many([_fail_key(email), _lock_key(email)])


def lockout_remaining_seconds(email: str) -> int:
    # Redis backend: TTL available via .ttl(); locmem не поддерживает → возвращаем фикс.
    # Для унификации делаем простую оценку (не критично).
    return LOCKOUT_MINUTES * 60
