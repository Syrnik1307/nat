"""Helper utilities for user notification delivery."""
from datetime import timedelta
import logging
from typing import Dict, Optional

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


NOTIFICATION_FIELD_MAP: Dict[str, str] = {
    # Базовые — учителю
    'homework_submitted': 'notify_homework_submitted',
    'subscription_expiring': 'notify_subscription_expiring',
    'payment_success': 'notify_payment_success',

    # Базовые — ученику
    'homework_graded': 'notify_homework_graded',
    'homework_regraded': 'notify_homework_regraded',
    'homework_deadline': 'notify_homework_deadline',
    'lesson_reminder': 'notify_lesson_reminders',
    'new_homework': 'notify_new_homework',

    # Аналитика — учителю
    'absence_alert': 'notify_absence_alert',
    'performance_drop_alert': 'notify_performance_drop',
    'group_health_alert': 'notify_group_health',
    'grading_backlog': 'notify_grading_backlog',
    'inactive_student_alert': 'notify_inactive_student',
    
    # Новые события — учителю
    'student_joined': 'notify_student_joined',
    'student_left': 'notify_student_left',
    'recording_ready': 'notify_recording_ready',
    
    # Новые события — ученику
    'lesson_link_sent': 'notify_lesson_reminders',  # Использует общую настройку уроков
    'materials_added': 'notify_new_homework',  # Использует настройку новых материалов/ДЗ
    'welcome_to_group': 'notify_lesson_reminders',  # Всегда отправляем приветствие

    # Аналитика — ученику
    'student_absence_warning': 'notify_student_absence_warning',
    'control_point_deadline': 'notify_control_point_deadline',
    'achievement': 'notify_achievement',
    'student_inactivity_nudge': 'notify_inactivity_nudge',

    # Хранилище (совместимость)
    'storage_quota_warning': 'notify_lesson_reminders',
    'storage_quota_exceeded': 'notify_lesson_reminders',
    'storage_warning': 'notify_lesson_reminders',
    'storage_limit_exceeded': 'notify_lesson_reminders',
    'recording_available': 'notify_lesson_reminders',
}


def is_notification_muted(
    user,
    notification_type: str,
    *,
    group=None,
    student=None,
) -> bool:
    """
    Проверяет, заглушено ли уведомление для данного пользователя.
    
    Args:
        user: Пользователь (обычно учитель)
        notification_type: Тип уведомления
        group: Группа (schedule.Group) - если уведомление связано с группой
        student: Ученик (CustomUser) - если уведомление связано с учеником
        
    Returns:
        bool: True если уведомление заглушено
    """
    from .models import NotificationMute
    
    if not user:
        return False
    
    # Проверяем mute по группе
    if group:
        mute = NotificationMute.objects.filter(
            user=user,
            mute_type='group',
            group=group,
        ).first()
        if mute:
            # Если muted_notification_types пусто - заглушены все
            if not mute.muted_notification_types:
                return True
            # Иначе проверяем конкретный тип
            if notification_type in mute.muted_notification_types:
                return True
    
    # Проверяем mute по ученику
    if student:
        mute = NotificationMute.objects.filter(
            user=user,
            mute_type='student',
            student=student,
        ).first()
        if mute:
            if not mute.muted_notification_types:
                return True
            if notification_type in mute.muted_notification_types:
                return True
    
    return False


def _get_bot_token() -> str:
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token or token == 'YOUR_BOT_TOKEN_HERE':
        return ''
    return token


def send_telegram_notification(user, notification_type: str, message: str, *, disable_web_page_preview: bool = True, silent: bool = False) -> bool:
    """Send a Telegram message respecting user notification preferences."""
    from .models import NotificationSettings, NotificationLog
    
    if not user:
        return False

    token = _get_bot_token()
    if not token:
        logger.warning('Telegram bot token is not configured. Skipping notification %s', notification_type)
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='skipped',
            message=message,
            error_message='TELEGRAM_BOT_TOKEN not configured'
        )
        return False

    settings_obj, _ = NotificationSettings.objects.get_or_create(user=user)
    field_name = NOTIFICATION_FIELD_MAP.get(notification_type)

    if not settings_obj.telegram_enabled:
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='skipped',
            message=message,
            error_message='Telegram notifications disabled by user'
        )
        return False

    if field_name and not getattr(settings_obj, field_name, True):
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='skipped',
            message=message,
            error_message=f'{field_name} disabled'
        )
        return False

    if not user.telegram_chat_id:
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='skipped',
            message=message,
            error_message='Missing telegram_chat_id'
        )
        return False

    # Dedupe: avoid sending identical notifications repeatedly due to retries / double-dispatch
    # (e.g., Celery task + synchronous fallback).
    dedupe_window = timezone.now() - timedelta(minutes=2)
    if NotificationLog.objects.filter(
        user=user,
        notification_type=notification_type,
        channel='telegram',
        status='sent',
        message=message,
        created_at__gte=dedupe_window,
    ).exists():
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='skipped',
            message=message,
            error_message='Deduped: identical recent notification'
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': user.telegram_chat_id,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': disable_web_page_preview,
        'disable_notification': silent,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            NotificationLog.objects.create(
                user=user,
                notification_type=notification_type,
                channel='telegram',
                status='sent',
                message=message,
            )
            return True
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='failed',
            message=message,
            error_message=response.text[:500],
        )
        logger.warning('Telegram API returned %s: %s', response.status_code, response.text)
        return False
    except requests.RequestException as exc:
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='failed',
            message=message,
            error_message=str(exc)
        )
        logger.exception('Failed to send Telegram notification: %s', exc)
        return False


def send_telegram_to_group_chat(chat_id: str, message: str, *, notification_source: str = 'lesson_reminder', disable_web_page_preview: bool = True, silent: bool = False) -> bool:
    """Отправляет сообщение в Telegram-группу по chat_id.
    
    Args:
        chat_id: ID группового чата в Telegram (может начинаться с '-')
        message: Текст сообщения
        notification_source: Источник уведомления для логирования
        disable_web_page_preview: Отключить превью ссылок
        silent: Отправить без звука
        
    Returns:
        bool: True если сообщение успешно отправлено
    """
    if not chat_id:
        logger.warning('send_telegram_to_group_chat: chat_id is empty')
        return False
    
    token = _get_bot_token()
    if not token:
        logger.warning('Telegram bot token is not configured. Skipping group notification.')
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': disable_web_page_preview,
        'disable_notification': silent,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            logger.info('Telegram group message sent to %s (%s)', chat_id, notification_source)
            return True
        else:
            error_text = response.text[:500]
            logger.warning('Telegram API error for group %s: %s - %s', chat_id, response.status_code, error_text)
            return False
    except requests.RequestException as exc:
        logger.exception('Failed to send Telegram group notification to %s (%s): %s', chat_id, notification_source, exc)
        return False


# =============================================================================
# Специализированные функции уведомлений
# =============================================================================

def notify_teacher_student_joined(teacher, student, group_name: str, is_individual: bool = False, group=None) -> bool:
    """Уведомить учителя о вступлении ученика в группу или к индивидуальным занятиям.
    
    Args:
        teacher: Учитель (CustomUser)
        student: Ученик (CustomUser)
        group_name: Название группы или предмета
        is_individual: True если это индивидуальный ученик
        group: Объект группы для проверки mutes
        
    Returns:
        bool: Успешность отправки
    """
    # Проверяем mutes
    if is_notification_muted(teacher, 'student_joined', group=group, student=student):
        logger.info('Notification muted for teacher %s: student_joined (student=%s, group=%s)', 
                    teacher.email, student.email if student else None, group_name)
        return False
    
    student_name = student.get_full_name() or student.email
    
    if is_individual:
        message = f"Новый индивидуальный ученик\n\n{student_name} присоединился к занятиям по предмету \"{group_name}\"."
    else:
        message = f"Новый ученик в группе\n\n{student_name} вступил в группу \"{group_name}\"."
    
    return send_telegram_notification(teacher, 'student_joined', message)


def notify_teacher_student_left(teacher, student, group_name: str, group=None) -> bool:
    """Уведомить учителя о выходе ученика из группы.
    
    Args:
        teacher: Учитель (CustomUser)
        student: Ученик (CustomUser)
        group_name: Название группы
        group: Объект группы для проверки mutes
        
    Returns:
        bool: Успешность отправки
    """
    # Проверяем mutes
    if is_notification_muted(teacher, 'student_left', group=group, student=student):
        logger.info('Notification muted for teacher %s: student_left (student=%s, group=%s)', 
                    teacher.email, student.email if student else None, group_name)
        return False
    
    student_name = student.get_full_name() or student.email
    message = f"Ученик покинул группу\n\n{student_name} вышел из группы \"{group_name}\"."
    
    return send_telegram_notification(teacher, 'student_left', message)


def notify_student_welcome(student, group_name: str, teacher_name: str) -> bool:
    """Отправить ученику приветственное сообщение при вступлении в группу.
    
    Args:
        student: Ученик (CustomUser)
        group_name: Название группы
        teacher_name: Имя преподавателя
        
    Returns:
        bool: Успешность отправки
    """
    message = (
        f"Добро пожаловать в Lectio Space\n\n"
        f"Вы успешно присоединились к группе \"{group_name}\".\n"
        f"Преподаватель: {teacher_name}\n\n"
        f"Ожидайте уведомления о предстоящих занятиях."
    )
    
    return send_telegram_notification(student, 'welcome_to_group', message)


def notify_lesson_link(lesson, join_url: str, platform: str = 'zoom') -> dict:
    """Отправить ссылку на урок ученикам группы.
    
    Отправляет ссылку:
    - В Telegram-группу (если привязана)
    - В личные сообщения каждому ученику (если подключен Telegram)
    
    Args:
        lesson: Урок (Lesson)
        join_url: Ссылка для подключения
        platform: 'zoom' или 'google_meet'
        
    Returns:
        dict: Статистика отправки {sent_to_group, sent_to_students, failed}
    """
    from .models import NotificationSettings
    
    result = {'sent_to_group': False, 'sent_to_students': 0, 'failed': 0}
    
    if not lesson.group:
        return result
    
    group = lesson.group
    teacher = lesson.teacher
    
    # Проверяем настройки учителя
    try:
        settings_obj = NotificationSettings.objects.get(user=teacher)
    except NotificationSettings.DoesNotExist:
        settings_obj = None
    
    # Определяем куда отправлять
    send_to_group = True
    send_to_students = True
    
    if settings_obj:
        if not settings_obj.notify_lesson_link_on_start:
            return result
        send_to_group = settings_obj.default_notify_to_group_chat
        send_to_students = settings_obj.default_notify_to_students_dm
    
    # Формируем сообщение
    lesson_title = lesson.title or group.name
    platform_name = 'Google Meet' if platform == 'google_meet' else 'Zoom'
    teacher_name = teacher.get_full_name() or teacher.email
    
    message = (
        f"Урок начинается\n\n"
        f"{lesson_title}\n"
        f"Преподаватель: {teacher_name}\n\n"
        f"Подключиться ({platform_name}):\n{join_url}"
    )
    
    # 1. Отправка в Telegram-группу
    if send_to_group and group.telegram_chat_id:
        if send_telegram_to_group_chat(group.telegram_chat_id, message, notification_source='lesson_link_sent'):
            result['sent_to_group'] = True
    
    # 2. Отправка ученикам в личку
    if send_to_students:
        students = group.students.filter(
            is_active=True,
            telegram_chat_id__isnull=False,
            telegram_verified=True
        ).exclude(telegram_chat_id='')
        
        for student in students:
            if send_telegram_notification(student, 'lesson_link_sent', message):
                result['sent_to_students'] += 1
            else:
                result['failed'] += 1
    
    return result


def notify_recording_ready_to_teacher(teacher, lesson, recording) -> bool:
    """Уведомить учителя о готовности записи урока.
    
    Args:
        teacher: Учитель (CustomUser)
        lesson: Урок (Lesson)
        recording: Запись (LessonRecording)
        
    Returns:
        bool: Успешность отправки
    """
    lesson_title = lesson.title or (lesson.group.name if lesson.group else 'Урок')
    lesson_date = lesson.start_time.strftime('%d.%m.%Y') if lesson.start_time else ''
    
    message = (
        f"Запись урока готова\n\n"
        f"Урок: {lesson_title}\n"
        f"Дата: {lesson_date}\n\n"
        f"Запись обработана и доступна для просмотра в разделе Записи."
    )
    
    return send_telegram_notification(teacher, 'recording_ready', message)


def notify_materials_added_to_students(lesson, material_title: str, material_type: str) -> dict:
    """Уведомить учеников о добавлении новых материалов к уроку.
    
    Args:
        lesson: Урок (Lesson)
        material_title: Название материала
        material_type: Тип материала (notes, document, miro)
        
    Returns:
        dict: Статистика {sent_to_group, sent_to_students, failed}
    """
    from .models import NotificationSettings
    
    result = {'sent_to_group': False, 'sent_to_students': 0, 'failed': 0}
    
    if not lesson.group:
        return result
    
    group = lesson.group
    teacher = lesson.teacher
    
    # Проверяем настройки учителя
    try:
        settings_obj = NotificationSettings.objects.get(user=teacher)
        if not settings_obj.notify_materials_added:
            return result
        send_to_group = settings_obj.default_notify_to_group_chat
        send_to_students = settings_obj.default_notify_to_students_dm
    except NotificationSettings.DoesNotExist:
        send_to_group = True
        send_to_students = True
    
    # Формируем сообщение
    type_names = {
        'notes': 'конспект',
        'document': 'документ',
        'miro': 'доска Miro',
    }
    type_name = type_names.get(material_type, 'материал')
    lesson_title = lesson.title or group.name
    
    message = (
        f"Новый {type_name}\n\n"
        f"К уроку \"{lesson_title}\" добавлен новый материал:\n"
        f"{material_title}\n\n"
        f"Посмотреть можно в разделе Материалы."
    )
    
    # 1. Отправка в Telegram-группу
    if send_to_group and group.telegram_chat_id:
        if send_telegram_to_group_chat(group.telegram_chat_id, message, notification_source='materials_added'):
            result['sent_to_group'] = True
    
    # 2. Отправка ученикам в личку
    if send_to_students:
        students = group.students.filter(
            is_active=True,
            telegram_chat_id__isnull=False,
            telegram_verified=True
        ).exclude(telegram_chat_id='')
        
        for student in students:
            if send_telegram_notification(student, 'materials_added', message):
                result['sent_to_students'] += 1
            else:
                result['failed'] += 1
    
    return result


def notify_lesson_reminder_with_link(lesson, minutes_before: int) -> dict:
    """Отправить напоминание об уроке (анонс) с возможной ссылкой.
    
    Используется для отправки напоминаний за N минут до урока.
    Ссылка включается только если она уже есть (урок запущен ранее).
    
    Args:
        lesson: Урок (Lesson)
        minutes_before: За сколько минут до урока
        
    Returns:
        dict: Статистика {sent_to_group, sent_to_students, failed}
    """
    from .models import NotificationSettings
    
    result = {'sent_to_group': False, 'sent_to_students': 0, 'failed': 0}
    
    if not lesson.group:
        return result
    
    group = lesson.group
    teacher = lesson.teacher
    
    # Проверяем настройки учителя
    try:
        settings_obj = NotificationSettings.objects.get(user=teacher)
        if not settings_obj.default_lesson_reminder_enabled:
            return result
        send_to_group = settings_obj.default_notify_to_group_chat
        send_to_students = settings_obj.default_notify_to_students_dm
    except NotificationSettings.DoesNotExist:
        send_to_group = True
        send_to_students = True
    
    # Формируем сообщение
    lesson_title = lesson.title or group.name
    teacher_name = teacher.get_full_name() or teacher.email
    start_time = lesson.start_time.strftime('%H:%M') if lesson.start_time else ''
    
    # Определяем текст времени
    if minutes_before <= 5:
        time_text = 'через 5 минут'
    elif minutes_before <= 15:
        time_text = 'через 15 минут'
    elif minutes_before <= 30:
        time_text = 'через 30 минут'
    elif minutes_before <= 60:
        time_text = 'через час'
    else:
        time_text = f'через {minutes_before} минут'
    
    message = (
        f"Напоминание об уроке\n\n"
        f"{lesson_title}\n"
        f"Начало: {start_time} ({time_text})\n"
        f"Преподаватель: {teacher_name}"
    )
    
    # Добавляем ссылку если есть
    join_url = lesson.google_meet_link or lesson.zoom_join_url
    if join_url:
        platform = 'Google Meet' if lesson.google_meet_link else 'Zoom'
        message += f"\n\nПодключиться ({platform}):\n{join_url}"
    else:
        message += "\n\nСсылка для подключения будет отправлена когда преподаватель начнёт урок."
    
    # 1. Отправка в Telegram-группу
    if send_to_group and group.telegram_chat_id:
        if send_telegram_to_group_chat(group.telegram_chat_id, message, notification_source='lesson_reminder'):
            result['sent_to_group'] = True
    
    # 2. Отправка ученикам в личку
    if send_to_students:
        students = group.students.filter(
            is_active=True,
            telegram_chat_id__isnull=False,
            telegram_verified=True
        ).exclude(telegram_chat_id='')
        
        for student in students:
            if send_telegram_notification(student, 'lesson_reminder', message):
                result['sent_to_students'] += 1
            else:
                result['failed'] += 1
    
    return result


def _get_payments_bot_token() -> str:
    """Получить токен отдельного бота для уведомлений о платежах."""
    token = getattr(settings, 'TELEGRAM_PAYMENTS_BOT_TOKEN', '')
    if not token or token == 'YOUR_BOT_TOKEN_HERE':
        return ''
    return token


def _send_payments_bot_message(text: str) -> bool:
    """
    Отправить сообщение через бота платежей в админский чат.
    
    Args:
        text: Текст сообщения
        
    Returns:
        bool: True если успешно
    """
    token = _get_payments_bot_token()
    chat_id = getattr(settings, 'ADMIN_PAYMENT_TELEGRAM_CHAT_ID', '')
    
    if not token or not chat_id:
        logger.warning('Payments bot token or chat ID not configured')
        return False
    
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
        }, timeout=10)
        if response.status_code == 200:
            return True
        logger.warning('Failed to send payments bot message: %s %s', response.status_code, response.text)
        return False
    except requests.RequestException as exc:
        logger.exception('Failed to send payments bot message: %s', exc)
        return False


def notify_admin_payment(
    payment,
    subscription,
    plan_name: Optional[str] = None,
    storage_gb: Optional[int] = None,
    *,
    zoom_addon: bool = False,
) -> bool:
    """
    Отправить уведомление админу о новом платеже.
    
    Использует отдельного бота (TELEGRAM_PAYMENTS_BOT_TOKEN) для уведомлений о платежах.
    
    Args:
        payment: Объект Payment
        subscription: Объект Subscription
        plan_name: Название плана (если оплата подписки)
        storage_gb: Количество ГБ (если оплата хранилища)
        
    Returns:
        bool: True если уведомление отправлено
    """
    # Chat ID админа для уведомлений о платежах
    admin_chat_id = getattr(settings, 'ADMIN_PAYMENT_TELEGRAM_CHAT_ID', None)
    if not admin_chat_id:
        logger.debug('ADMIN_PAYMENT_TELEGRAM_CHAT_ID not configured, skipping admin notification')
        return False
    
    # Используем отдельного бота для уведомлений о платежах
    token = _get_payments_bot_token()
    if not token:
        logger.warning('TELEGRAM_PAYMENTS_BOT_TOKEN not configured, cannot notify admin about payment')
        return False
    
    user = subscription.user
    user_info = user.get_full_name() or user.email
    
    # Формируем сообщение
    if zoom_addon:
        payment_type = "Zoom (подписка)"
    elif plan_name:
        payment_type = f"Подписка ({plan_name})"
    elif storage_gb:
        payment_type = f"Хранилище (+{storage_gb} ГБ)"
    else:
        payment_type = "Оплата"
    
    message = (
        f"Новая оплата\n\n"
        f"Пользователь: {user_info}\n"
        f"Email: {user.email}\n"
        f"Тип: {payment_type}\n"
        f"Сумма: {payment.amount} {payment.currency}\n"
        f"Платёжная система: {payment.payment_system}\n"
        f"ID платежа: {payment.payment_id}"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': admin_chat_id,
        'text': message,
        'disable_web_page_preview': True,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            logger.info(f'Admin payment notification sent for payment {payment.payment_id}')
            return True
        logger.warning(f'Failed to send admin payment notification: {response.status_code} {response.text}')
        return False
    except requests.RequestException as exc:
        logger.exception(f'Failed to send admin payment notification: {exc}')
        return False


def notify_payment_failed(
    payment,
    subscription,
    *,
    reason: Optional[str] = None,
    zoom_addon: bool = False,
) -> bool:
    """Уведомить админа о неуспешной оплате."""
    admin_chat_id = getattr(settings, 'ADMIN_PAYMENT_TELEGRAM_CHAT_ID', None)
    if not admin_chat_id:
        logger.debug('ADMIN_PAYMENT_TELEGRAM_CHAT_ID not configured, skipping payment-failed notification')
        return False

    token = _get_payments_bot_token()
    if not token:
        logger.warning('TELEGRAM_PAYMENTS_BOT_TOKEN not configured, cannot notify admin about failed payment')
        return False

    user = subscription.user
    user_info = user.get_full_name() or user.email
    payment_type = "Zoom (подписка)" if zoom_addon else "Оплата"
    reason_text = f"\nПричина: {reason}" if reason else ''

    message = (
        f"Оплата не прошла\n\n"
        f"Пользователь: {user_info}\n"
        f"Email: {user.email}\n"
        f"Тип: {payment_type}\n"
        f"Сумма: {payment.amount} {payment.currency}\n"
        f"Платёжная система: {payment.payment_system}\n"
        f"ID платежа: {payment.payment_id}"
        f"{reason_text}"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': admin_chat_id,
        'text': message,
        'disable_web_page_preview': True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            logger.info('Admin payment-failed notification sent for payment %s', getattr(payment, 'payment_id', None))
            return True
        logger.warning('Failed to send admin payment-failed notification: %s %s', response.status_code, response.text)
        return False
    except requests.RequestException as exc:
        logger.exception('Failed to send admin payment-failed notification: %s', exc)
        return False


def notify_payment_refunded(
    payment,
    subscription,
    *,
    amount: Optional[str] = None,
    zoom_addon: bool = False,
) -> bool:
    """Уведомить админа о возврате платежа."""
    admin_chat_id = getattr(settings, 'ADMIN_PAYMENT_TELEGRAM_CHAT_ID', None)
    if not admin_chat_id:
        logger.debug('ADMIN_PAYMENT_TELEGRAM_CHAT_ID not configured, skipping refunded notification')
        return False

    token = _get_payments_bot_token()
    if not token:
        logger.warning('TELEGRAM_PAYMENTS_BOT_TOKEN not configured, cannot notify admin about refund')
        return False

    user = subscription.user
    user_info = user.get_full_name() or user.email
    payment_type = "Zoom (подписка)" if zoom_addon else "Оплата"
    refunded_amount = amount or f"{payment.amount} {payment.currency}"

    message = (
        f"Возврат платежа\n\n"
        f"Пользователь: {user_info}\n"
        f"Email: {user.email}\n"
        f"Тип: {payment_type}\n"
        f"Сумма: {refunded_amount}\n"
        f"Платёжная система: {payment.payment_system}\n"
        f"ID платежа: {payment.payment_id}"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': admin_chat_id,
        'text': message,
        'disable_web_page_preview': True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            logger.info('Admin refunded notification sent for payment %s', getattr(payment, 'payment_id', None))
            return True
        logger.warning('Failed to send admin refunded notification: %s %s', response.status_code, response.text)
        return False
    except requests.RequestException as exc:
        logger.exception('Failed to send admin refunded notification: %s', exc)
        return False


def notify_auto_renewal_success(subscription, user, renewal_type: str) -> bool:
    """Уведомить пользователя об успешном автопродлении.

    renewal_type:
      - 'subscription' (основная подписка)
      - 'zoom_addon' (Zoom-дополнение)
    """
    if not user:
        return False

    if renewal_type == 'zoom_addon':
        expires_at = getattr(subscription, 'zoom_addon_expires_at', None)
        until = expires_at.strftime('%d.%m.%Y') if expires_at else None
        message = 'Автопродление Zoom-подписки прошло успешно.'
        if until:
            message += f"\nДействует до {until}"
    else:
        expires_at = getattr(subscription, 'expires_at', None)
        until = expires_at.strftime('%d.%m.%Y') if expires_at else None
        message = 'Автопродление подписки прошло успешно.'
        if until:
            message += f"\nДействует до {until}"

    return send_telegram_notification(user, 'payment_success', message)


def notify_student_top_rating(student, rank: int, period_type: str, period_label: str, group_name: str, total_points: int) -> bool:
    """
    Отправляет уведомление ученику о попадании в топ рейтинга.
    
    Args:
        student: Пользователь-ученик
        rank: Место в рейтинге (1, 2, 3)
        period_type: 'month' или 'season'
        period_label: Название периода (например, "Январь 2026" или "Зима 2025-2026")
        group_name: Название группы
        total_points: Всего баллов
    
    Returns:
        bool: True если уведомление отправлено
    """
    if rank == 1:
        medal = "1 место"
        emoji_line = "Вы заняли первое место!"
    elif rank == 2:
        medal = "2 место"
        emoji_line = "Вы заняли второе место!"
    elif rank == 3:
        medal = "3 место"
        emoji_line = "Вы заняли третье место!"
    else:
        return False  # Уведомляем только топ-3
    
    period_name = "месяц" if period_type == 'month' else "сезон"
    
    message = (
        f"Поздравляем! {emoji_line}\n\n"
        f"Группа: {group_name}\n"
        f"Период: {period_label}\n"
        f"Рейтинг: {medal}\n"
        f"Баллы: {total_points}\n\n"
        f"Так держать! Продолжайте в том же духе."
    )
    
    return send_telegram_notification(student, 'achievement', message)


def get_season_info(date=None):
    """
    Возвращает информацию о сезоне для указанной даты.
    
    Returns:
        tuple: (season_name, season_start_month, season_end_month, season_label)
    """
    if date is None:
        date = timezone.now()
    
    month = date.month
    year = date.year
    
    if month in [12, 1, 2]:
        # Зима: декабрь прошлого года - февраль текущего
        start_year = year - 1 if month == 12 else year
        season_label = f"Зима {start_year}-{start_year + 1}" if month == 12 else f"Зима {year - 1}-{year}"
        return ('winter', 12, 2, season_label)
    elif month in [3, 4, 5]:
        return ('spring', 3, 5, f"Весна {year}")
    elif month in [6, 7, 8]:
        return ('summer', 6, 8, f"Лето {year}")
    else:  # 9, 10, 11
        return ('autumn', 9, 11, f"Осень {year}")


# =============================================================================
# Уведомления об автопродлениях и churn
# =============================================================================

def notify_auto_renewal_success(subscription, user, renewal_type: str = 'subscription') -> bool:
    """
    Уведомление админа об успешном автопродлении подписки или Zoom add-on.
    
    Args:
        subscription: Subscription instance
        user: User who owns the subscription
        renewal_type: 'subscription' или 'zoom_addon'
    """
    token = _get_payments_bot_token()
    chat_id = getattr(settings, 'ADMIN_PAYMENT_TELEGRAM_CHAT_ID', '')
    
    if not token or not chat_id:
        logger.warning('Payments bot token or chat ID not configured')
        return False
    
    if renewal_type == 'zoom_addon':
        type_label = 'Zoom Add-on'
        expires_at = subscription.zoom_addon_expires_at
    else:
        type_label = 'Подписка'
        expires_at = subscription.expires_at
    
    expires_str = expires_at.strftime('%d.%m.%Y %H:%M') if expires_at else 'не указано'
    
    lines = [
        'АВТОПРОДЛЕНИЕ УСПЕШНО',
        '',
        f'Тип: {type_label}',
        f'Пользователь: {user.email}',
        f'ID подписки: {subscription.id}',
        f'Действует до: {expires_str}',
    ]
    
    text = '\n'.join(lines)
    return _send_payments_bot_message(text)


def notify_auto_renewal_failed(subscription, user, renewal_type: str = 'subscription', reason: str = '') -> bool:
    """
    Уведомление админа о неудачном автопродлении.
    
    Args:
        subscription: Subscription instance
        user: User who owns the subscription
        renewal_type: 'subscription' или 'zoom_addon'
        reason: Причина неудачи
    """
    token = _get_payments_bot_token()
    chat_id = getattr(settings, 'ADMIN_PAYMENT_TELEGRAM_CHAT_ID', '')
    
    if not token or not chat_id:
        logger.warning('Payments bot token or chat ID not configured')
        return False
    
    type_label = 'Zoom Add-on' if renewal_type == 'zoom_addon' else 'Подписка'
    
    lines = [
        'АВТОПРОДЛЕНИЕ НЕ УДАЛОСЬ',
        '',
        f'Тип: {type_label}',
        f'Пользователь: {user.email}',
        f'ID подписки: {subscription.id}',
        f'Причина: {reason or "неизвестно"}',
        '',
        'Автопродление отключено для этой подписки.',
    ]
    
    text = '\n'.join(lines)
    return _send_payments_bot_message(text)


def notify_subscription_expiring_no_payment(subscription, user, days_left: int) -> bool:
    """
    Churn warning: уведомление админа о том, что подписка истекает без настроенного автопродления.
    
    Args:
        subscription: Subscription instance
        user: User who owns the subscription
        days_left: Дней до истечения
    """
    token = _get_payments_bot_token()
    chat_id = getattr(settings, 'ADMIN_PAYMENT_TELEGRAM_CHAT_ID', '')
    
    if not token or not chat_id:
        logger.warning('Payments bot token or chat ID not configured')
        return False
    
    expires_str = subscription.expires_at.strftime('%d.%m.%Y') if subscription.expires_at else 'не указано'
    total_paid = subscription.total_paid or 0
    
    lines = [
        'ПОДПИСКА ИСТЕКАЕТ (без автопродления)',
        '',
        f'Пользователь: {user.email}',
        f'Осталось дней: {days_left}',
        f'Истекает: {expires_str}',
        f'Всего оплачено: {total_paid} RUB',
        '',
        'Рекомендация: связаться с пользователем.',
    ]
    
    text = '\n'.join(lines)
    return _send_payments_bot_message(text)


def send_weekly_revenue_report() -> bool:
    """
    Отправляет еженедельный отчёт о выручке в Telegram бот платежей.
    
    Считает:
    - Общую выручку за неделю
    - Разбивку по типам (подписки/хранилище/zoom)
    - Сравнение с предыдущей неделей
    """
    from datetime import timedelta
    from decimal import Decimal
    from .models import Payment
    
    token = _get_payments_bot_token()
    chat_id = getattr(settings, 'ADMIN_PAYMENT_TELEGRAM_CHAT_ID', '')
    
    if not token or not chat_id:
        logger.warning('Payments bot token or chat ID not configured')
        return False
    
    now = timezone.now()
    
    # Текущая неделя (последние 7 дней)
    week_start = now - timedelta(days=7)
    current_week_payments = Payment.objects.filter(
        status=Payment.STATUS_SUCCEEDED,
        paid_at__gte=week_start,
        paid_at__lt=now,
    )
    
    # Предыдущая неделя
    prev_week_start = week_start - timedelta(days=7)
    prev_week_payments = Payment.objects.filter(
        status=Payment.STATUS_SUCCEEDED,
        paid_at__gte=prev_week_start,
        paid_at__lt=week_start,
    )
    
    # Считаем суммы по типам
    def calc_revenue(payments):
        subscriptions = Decimal('0')
        storage = Decimal('0')
        zoom = Decimal('0')
        
        for p in payments:
            meta = p.metadata or {}
            if meta.get('zoom_addon'):
                zoom += p.amount
            elif meta.get('storage_gb'):
                storage += p.amount
            else:
                subscriptions += p.amount
        
        return {
            'total': subscriptions + storage + zoom,
            'subscriptions': subscriptions,
            'storage': storage,
            'zoom': zoom,
            'count': payments.count(),
        }
    
    current = calc_revenue(current_week_payments)
    previous = calc_revenue(prev_week_payments)
    
    # Расчёт изменения в процентах
    if previous['total'] > 0:
        change_pct = ((current['total'] - previous['total']) / previous['total']) * 100
        change_str = f"+{change_pct:.1f}%" if change_pct >= 0 else f"{change_pct:.1f}%"
    else:
        change_str = "N/A (прошлая неделя: 0)"
    
    # Форматируем даты
    week_start_str = week_start.strftime('%d.%m.%Y')
    now_str = now.strftime('%d.%m.%Y')
    
    lines = [
        'ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ О ВЫРУЧКЕ',
        '',
        f'Период: {week_start_str} - {now_str}',
        '',
        f'Общая выручка: {current["total"]} RUB',
        f'Платежей: {current["count"]}',
        '',
        'Разбивка:',
        f'  Подписки: {current["subscriptions"]} RUB',
        f'  Хранилище: {current["storage"]} RUB',
        f'  Zoom Add-on: {current["zoom"]} RUB',
        '',
        f'Сравнение с прошлой неделей: {change_str}',
        f'(прошлая неделя: {previous["total"]} RUB, {previous["count"]} платежей)',
    ]
    
    text = '\n'.join(lines)
    return _send_payments_bot_message(text)


