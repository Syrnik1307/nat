from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from .models import CustomUser, TelegramLinkCode, NotificationSettings


class TelegramVerificationError(Exception):
    """Raised when Telegram verification fails."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class TelegramLinkResult:
    user: CustomUser
    was_linked_before: bool


def generate_link_code_for_user(user: CustomUser, ttl_minutes: int = 10) -> TelegramLinkCode:
    """Helper to generate a fresh link code for the given user."""
    return TelegramLinkCode.generate_for_user(user, ttl_minutes=ttl_minutes)


def link_account_with_code(*, code: str, telegram_id: str, telegram_username: str = '', telegram_chat_id: str = '') -> TelegramLinkResult:
    """Validate the code and bind Telegram metadata to the owning user."""
    normalized_code = (code or '').strip().upper()
    if not normalized_code:
        raise TelegramVerificationError('empty_code', 'Код привязки не указан')

    try:
        link_code = TelegramLinkCode.objects.select_related('user').get(code=normalized_code)
    except TelegramLinkCode.DoesNotExist as exc:
        raise TelegramVerificationError('invalid_code', 'Код не найден. Запросите новый в профиле.') from exc

    if link_code.used:
        raise TelegramVerificationError('code_used', 'Этот код уже был использован. Сгенерируйте новый.')
    if link_code.expires_at < timezone.now():
        raise TelegramVerificationError('code_expired', 'Срок действия кода истёк. Создайте новый код в профиле.')

    user = link_code.user
    clean_telegram_id = str(telegram_id or '').strip()
    if not clean_telegram_id:
        raise TelegramVerificationError('empty_telegram_id', 'Отсутствует Telegram ID. Попробуйте ещё раз.')

    with transaction.atomic():
        # Проверяем, что Telegram ID не привязан к другому пользователю
        duplicate = CustomUser.objects.filter(telegram_id=clean_telegram_id).exclude(pk=user.pk).exists()
        if duplicate:
            raise TelegramVerificationError('telegram_in_use', 'Этот Telegram уже привязан к другому аккаунту.')

        was_linked = bool(user.telegram_id)
        user.telegram_id = clean_telegram_id
        user.telegram_username = telegram_username or ''
        user.telegram_chat_id = str(telegram_chat_id or '') or user.telegram_chat_id or ''
        user.telegram_verified = True
        user.save(update_fields=['telegram_id', 'telegram_username', 'telegram_chat_id', 'telegram_verified', 'updated_at'])

        # Включаем Telegram уведомления по умолчанию
        settings_obj, _ = NotificationSettings.objects.get_or_create(user=user)
        if not settings_obj.telegram_enabled:
            settings_obj.telegram_enabled = True
            settings_obj.save(update_fields=['telegram_enabled', 'updated_at'])

        link_code.mark_used()

    return TelegramLinkResult(user=user, was_linked_before=was_linked)


def unlink_user_telegram(user: CustomUser):
    """Сбрасывает Telegram-поля и отключает Telegram уведомления."""
    user.telegram_id = None
    user.telegram_username = ''
    user.telegram_chat_id = None
    user.telegram_verified = False
    user.save(update_fields=['telegram_id', 'telegram_username', 'telegram_chat_id', 'telegram_verified', 'updated_at'])

    settings_obj, _ = NotificationSettings.objects.get_or_create(user=user)
    if settings_obj.telegram_enabled:
        settings_obj.telegram_enabled = False
        settings_obj.save(update_fields=['telegram_enabled', 'updated_at'])
