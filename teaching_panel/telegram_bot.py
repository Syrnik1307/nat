"""
Telegram бот для восстановления пароля и привязки аккаунта
"""
import os
import django
import asyncio
import logging
from typing import List, Optional
from urllib.parse import urljoin

from django.conf import settings
from django.db.models import Prefetch, Q
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from asgiref.sync import sync_to_async

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import PasswordResetToken, NotificationSettings
from schedule.models import Lesson, RecurringLessonTelegramBindCode
from homework.models import Homework, StudentSubmission
from accounts.telegram_utils import (
    link_account_with_code,
    TelegramVerificationError,
    unlink_user_telegram,
)
from django.utils import timezone
from django.utils.crypto import get_random_string
from support.models import SupportTicket, SupportMessage

User = get_user_model()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получите токен от @BotFather в Telegram
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
DEFAULT_FRONTEND_URL = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
WEBAPP_URL = (os.environ.get('WEBAPP_URL') or DEFAULT_FRONTEND_URL or 'http://localhost:3000').rstrip('/')
RESET_PASSWORD_PATH = os.environ.get('RESET_PASSWORD_PATH', '/reset-password')

ROLE_EMOJI = {
    'student': '🎓',
    'teacher': '👨\u200d🏫',
    'admin': '⚙️',
}

ROLE_NAMES = {
    'student': 'Ученик',
    'teacher': 'Учитель',
    'admin': 'Администратор',
}


# Контекст поддержки в Telegram (in-memory): {telegram_id: {'ticket_id': int|None}}
support_context = {}


def _build_frontend_url(path: str = '') -> str:
    base = WEBAPP_URL.rstrip('/') + '/'
    relative = (path or '').lstrip('/')
    return urljoin(base, relative) if relative else WEBAPP_URL

MAIN_MENU_LAYOUT = [
    [
        InlineKeyboardButton('📅 Уроки', callback_data='menu:lessons'),
        InlineKeyboardButton('📝 Домашки', callback_data='menu:homework'),
    ],
    [
        InlineKeyboardButton('🔔 Уведомления', callback_data='menu:notifications'),
        InlineKeyboardButton('👤 Профиль', callback_data='menu:profile'),
    ],
    [InlineKeyboardButton('❓ Помощь', callback_data='menu:help')],
]

NOTIFICATION_FIELDS_META = {
    'telegram_enabled': {'label': 'Telegram канал', 'emoji': '📲', 'roles': None, 'short': 'Канал'},
    'notify_lesson_reminders': {'label': 'Напоминания об уроках', 'emoji': '⏰', 'roles': {'student'}, 'short': 'Уроки'},
    'notify_new_homework': {'label': 'Новое ДЗ', 'emoji': '🆕', 'roles': {'student'}, 'short': 'Новое ДЗ'},
    'notify_homework_deadline': {'label': 'Напоминания о дедлайнах', 'emoji': '📎', 'roles': {'student'}, 'short': 'Дедлайны'},
    'notify_homework_graded': {'label': 'Проверка ДЗ', 'emoji': '✅', 'roles': {'student'}, 'short': 'Проверка'},
    'notify_homework_submitted': {'label': 'ДЗ сдано учеником', 'emoji': '📝', 'roles': {'teacher'}, 'short': 'Сдачи'},
    'notify_payment_success': {'label': 'Платёж прошёл', 'emoji': '💳', 'roles': {'teacher', 'admin'}, 'short': 'Платежи'},
    'notify_subscription_expiring': {'label': 'Подписка истекает', 'emoji': '⚠️', 'roles': {'teacher', 'admin'}, 'short': 'Подписка'},
}

ROLE_SECTION_TITLES = {
    'student': '🎓 Уведомления ученика',
    'teacher': '👨\u200d🏫 Уведомления преподавателя',
}


def _notification_sections_for_user(user: User) -> List[str]:
    """Return ordered sections (roles) that current user may manage."""
    if getattr(user, 'role', None) == 'admin':
        return ['teacher', 'student']
    if getattr(user, 'role', None) in ROLE_SECTION_TITLES:
        return [user.role]
    return ['student']


def _fields_for_section(section_role: str) -> List[str]:
    return [
        field
        for field, meta in NOTIFICATION_FIELDS_META.items()
        if meta['roles'] and section_role in meta['roles']
    ]


def _role_badge(user: User) -> str:
    return f"{ROLE_EMOJI.get(user.role, '👤')} {ROLE_NAMES.get(user.role, user.role.title())}"


def _format_display_name(user: User) -> str:
    full = user.get_full_name() if hasattr(user, 'get_full_name') else ''
    return (full or user.first_name or user.email or 'Пользователь').strip()


def _build_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(MAIN_MENU_LAYOUT)


def _build_section_keyboard(section: str, include_refresh: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if include_refresh:
        rows.append([InlineKeyboardButton('🔄 Обновить', callback_data=f'menu:{section}')])
    rows.append([InlineKeyboardButton('⬅️ В главное меню', callback_data='menu:root')])
    return InlineKeyboardMarkup(rows)


async def _send_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    *,
    parse_mode: Optional[str] = 'Markdown',
    disable_preview: bool = True,
):
    common_kwargs = {
        'reply_markup': reply_markup,
        'disable_web_page_preview': disable_preview,
    }
    if parse_mode:
        common_kwargs['parse_mode'] = parse_mode

    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, **common_kwargs)
    elif update.message:
        await update.message.reply_text(text, **common_kwargs)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, **common_kwargs)


async def _get_linked_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[User]:
    telegram_id = str(update.effective_user.id)
    try:
        return await sync_to_async(User.objects.get)(telegram_id=telegram_id)
    except User.DoesNotExist:
        warning = '❌ Telegram ещё не привязан. Откройте Teaching Panel → Профиль → Безопасность и отправьте /start <код>.'
        if update.callback_query:
            await update.callback_query.answer('Привяжите аккаунт через /start', show_alert=True)
        if update.effective_chat:
            await context.bot.send_message(update.effective_chat.id, warning)
        return None


async def _fetch_upcoming_lessons(user: User, limit: int = 5) -> List[Lesson]:
    def query():
        now = timezone.now()
        qs = Lesson.objects.select_related('group', 'teacher').filter(start_time__gte=now)
        if user.role == 'teacher':
            qs = qs.filter(teacher=user)
        elif user.role == 'student':
            qs = qs.filter(group__students=user)
        else:
            qs = qs.filter(Q(teacher=user) | Q(group__students=user))
        return list(qs.order_by('start_time').distinct()[:limit])

    return await sync_to_async(query)()


async def _fetch_student_homeworks(user: User, limit: int = 5) -> List[Homework]:
    def query():
        submissions_prefetch = Prefetch(
            'submissions',
            queryset=StudentSubmission.objects.filter(student=user),
            to_attr='student_submissions',
        )
        qs = (
            Homework.objects.select_related('teacher', 'lesson', 'lesson__group')
            .prefetch_related(submissions_prefetch)
            .filter(lesson__group__students=user)
            .order_by('-created_at')
        )
        return list(qs.distinct()[:limit])

    return await sync_to_async(query)()


async def _fetch_teacher_submissions(user: User, limit: int = 5) -> List[StudentSubmission]:
    def query():
        qs = (
            StudentSubmission.objects.select_related('student', 'homework', 'homework__lesson', 'homework__lesson__group')
            .filter(homework__teacher=user, status='submitted')
            .order_by('-submitted_at')
        )
        return list(qs[:limit])

    return await sync_to_async(query)()


def _format_lesson_entry(lesson: Lesson) -> str:
    start_local = timezone.localtime(lesson.start_time) if lesson.start_time else None
    start_line = start_local.strftime('%d.%m %H:%M') if start_local else 'скоро'
    teacher_name = _format_display_name(lesson.teacher)
    group_name = lesson.group.name if lesson.group else 'Без группы'
    zoom_line = f"\n🔗 Zoom: {lesson.zoom_join_url}" if lesson.zoom_join_url else ''
    return (
        f"• {start_line} — {lesson.title}\n"
        f"  Группа: {group_name}\n"
        f"  Преподаватель: {teacher_name}{zoom_line}"
    )


def _build_notification_message(user: User, settings_obj: NotificationSettings) -> str:
    def status(label: str) -> str:
        return '✅' if getattr(settings_obj, label, False) else '❌'

    lines = ["🔔 *Настройки уведомлений*\n"]
    lines.append(f"{NOTIFICATION_FIELDS_META['telegram_enabled']['emoji']} {NOTIFICATION_FIELDS_META['telegram_enabled']['label']}: {status('telegram_enabled')}")

    for section_role in _notification_sections_for_user(user):
        title = ROLE_SECTION_TITLES.get(section_role)
        fields = _fields_for_section(section_role)
        if not fields or not title:
            continue
        lines.append(f"\n{title}")
        for field in fields:
            meta = NOTIFICATION_FIELDS_META[field]
            lines.append(f"{meta['emoji']} {meta['label']}: {status(field)}")

    footer = {
        'teacher': '\nВы управляете только уведомлениями преподавателя.',
        'student': '\nВы управляете только уведомлениями ученика.',
        'admin': '\nВы администратор: отображаются настройки ученика и преподавателя, изменения касаются вашего Telegram.',
    }
    lines.append(footer.get(getattr(user, 'role', ''), '\nИзменения применяются только к вашему Telegram.'))
    lines.append('\nНажмите кнопку ниже, чтобы включить или выключить конкретное уведомление.')
    return '\n'.join(lines)


def _build_notification_keyboard(user: User, settings_obj: NotificationSettings) -> InlineKeyboardMarkup:
    ordered_fields: List[str] = ['telegram_enabled']
    for section_role in _notification_sections_for_user(user):
        ordered_fields.extend(_fields_for_section(section_role))

    # Deduplicate while preserving order (актуально для админа)
    seen = set()
    buttons = []
    for field in ordered_fields:
        if field in seen:
            continue
        seen.add(field)
        meta = NOTIFICATION_FIELDS_META[field]
        current = '✅' if getattr(settings_obj, field, False) else '❌'
        buttons.append(InlineKeyboardButton(f"{current} {meta['short']}", callback_data=f'notif_toggle:{field}'))

    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton('⬅️ В меню', callback_data='menu:root')])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start с поддержкой deep-link кода."""
    user = update.effective_user
    telegram_id = str(user.id)
    args = context.args if context.args else []

    if args:
        raw_arg = args[0].strip()
        normalized_arg = raw_arg.lower()

        # Специальный deep-link для мгновенного запуска /reset
        if normalized_arg in {'reset', 'reset_password', 'resetpass'}:
            await reset_password(update, context)
            return

        # Deep-link для поддержки:
        # - support (если уже привязан)
        # - support_<CODE> (если нужно сначала привязать)
        if normalized_arg == 'support':
            await support_start(update, context)
            return

        if normalized_arg.startswith('support_'):
            code = raw_arg.split('_', 1)[1].strip().upper()
            checking_msg = await update.message.reply_text("🔄 Проверяем код привязки...")
            try:
                result = await sync_to_async(link_account_with_code)(
                    code=code,
                    telegram_id=telegram_id,
                    telegram_username=user.username or '',
                    telegram_chat_id=str(update.effective_chat.id),
                )
                linked_user = result.user
                await checking_msg.delete()
                await update.message.reply_text("✅ Telegram привязан. Давайте оформим обращение в поддержку.")
                await support_start(update, context, linked_user)
            except TelegramVerificationError as exc:
                await checking_msg.delete()
                await update.message.reply_text(
                    f"❌ Не удалось привязать Telegram ({exc}).\n"
                    "Откройте Teaching Panel → Профиль → Безопасность и создайте новый код.",
                )
            return

        # По умолчанию — считаем аргумент кодом привязки
        code = raw_arg.upper()
        logger.info(f"[start] User {telegram_id} attempting link with code: {code}")

        checking_msg = await update.message.reply_text("🔄 Проверяем код привязки...")

        try:
            result = await sync_to_async(link_account_with_code)(
                code=code,
                telegram_id=telegram_id,
                telegram_username=user.username or '',
                telegram_chat_id=str(update.effective_chat.id),
            )
            linked_user = result.user
            logger.info(f"[start] Successfully linked {telegram_id} with code {code}")

            await checking_msg.delete()

            keyboard = [[InlineKeyboardButton("🌐 Открыть Teaching Panel", url=WEBAPP_URL)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "🎉 *Отлично! Аккаунт успешно привязан!*\n\n"
                f"✅ Email: `{linked_user.email}`\n"
                f"✅ Имя: {linked_user.first_name or 'Не указано'}\n\n"
                "💬 Команды:\n"
                "/menu — главное меню\n"
                "/profile — ваш профиль\n"
                "/reset — сбросить пароль\n"
                "/notifications — настройки уведомлений\n"
                "/support — написать в поддержку\n"
                "/close — закрыть обращение\n"
                "/unlink — отвязать аккаунт",
                parse_mode='Markdown',
                reply_markup=reply_markup,
            )
            await show_main_menu(update, context, linked_user)
        except TelegramVerificationError as exc:
            logger.error(f"[start] Link failed for {telegram_id}: {exc.code} - {exc}")
            await checking_msg.delete()

            error_details = {
                'empty_code': '❌ *Код не указан*\n\nПожалуйста, используйте ссылку из профиля Teaching Panel.',
                'invalid_code': '❌ *Код не найден*\n\nЭтот код недействителен или срок его действия истёк (коды действуют 10 минут).\n\nПожалуйста:\n1. Откройте Teaching Panel → Профиль → Безопасность\n2. Создайте новый код привязки\n3. Вернитесь в Telegram и откройте новую ссылку',
                'code_used': '❌ *Код уже использован*\n\nЭтот код уже был использован для привязки. Создайте новый код в профиле.',
                'code_expired': '❌ *Код истёк*\n\nСрок действия этого кода истёк (коды действуют 10 минут).\n\nПожалуйста создайте новый код в профиле Teaching Panel.',
                'telegram_in_use': '⚠️ *Этот Telegram уже привязан*\n\nВаш Telegram ID уже привязан к другому аккаунту Teaching Panel. Если это ваш аккаунт, сначала отвяжите его через /unlink.',
                'empty_telegram_id': '❌ *Ошибка Telegram ID*\n\nНе удалось получить ваш Telegram ID. Попробуйте ещё раз.'
            }

            error_msg = error_details.get(exc.code, f"❌ Ошибка привязки: {exc}")
            await update.message.reply_text(error_msg, parse_mode='Markdown')
        return

    # Проверяем, привязан ли уже аккаунт
    try:
        db_user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)
        await update.message.reply_text(
            f"👋 Привет, {db_user.first_name or user.first_name}!\n\n"
            f"✅ Аккаунт уже привязан.\n"
            f"📧 Email: {db_user.email}\n\n"
            "Попробуйте обновлённое меню:\n"
            "• /menu — быстрый доступ ко всем разделам\n"
            "• /lessons — ближайшие уроки\n"
            "• /homework — статусы домашних заданий\n"
            "• /notifications — настройки уведомлений\n"
            "• /reset — восстановление пароля\n"
            "• /unlink — отвязать Telegram"
        )
        await show_main_menu(update, context, db_user)
    except User.DoesNotExist:
        keyboard = [
            [InlineKeyboardButton("🔗 Как привязать аккаунт", callback_data='link_account')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"Я бот Teaching Panel. Чтобы пользоваться мной:\n\n"
            f"1. Откройте Teaching Panel → Профиль → вкладка 'Безопасность'\n"
            f"2. Создайте код привязки Telegram\n"
            f"3. Вернитесь в Telegram и отправьте /start <код>\n\n"
            f"Нажмите кнопку ниже, чтобы получить инструкцию ещё раз.",
            reply_markup=reply_markup
        )


async def link_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки привязки аккаунта"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = str(query.from_user.id)
    telegram_username = query.from_user.username or ''
    
    await query.edit_message_text(
        f"🔗 Новая инструкция по привязке:\n\n"
        f"1. Зайдите на {WEBAPP_URL}\n"
        f"2. Откройте Профиль → вкладку 'Безопасность'\n"
        f"3. Нажмите 'Получить код' в блоке Telegram\n"
        f"4. Вернитесь в этот чат и отправьте команду /start <код>\n\n"
        f"Ваш Telegram ID: `{telegram_id}`\n"
        f"Username: @{telegram_username}\n\n"
        f"После успешной привязки /start покажет статус",
        parse_mode='Markdown'
    )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user: Optional[User] = None):
    if not user:
        user = await _get_linked_user(update, context)
        if not user:
            return

    lessons = await _fetch_upcoming_lessons(user, limit=1)
    if lessons:
        lesson = lessons[0]
        start_local = timezone.localtime(lesson.start_time) if lesson.start_time else None
        start_str = start_local.strftime('%d.%m %H:%M') if start_local else 'скоро'
        summary_line = f"📅 Ближайший урок: {lesson.title} • {start_str}"
    else:
        summary_line = '📅 Ближайших уроков пока нет'

    text = (
        "✨ *Teaching Panel бот*\n"
        f"{_role_badge(user)} · {_format_display_name(user)}\n"
        f"{summary_line}\n\n"
        "Выберите действие на клавиатуре ниже 👇"
    )

    await _send_response(update, context, text, reply_markup=_build_main_menu_keyboard())


async def show_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_linked_user(update, context)
    if not user:
        return

    lessons = await _fetch_upcoming_lessons(user, limit=5)
    if lessons:
        lesson_text = '\n\n'.join(_format_lesson_entry(lesson) for lesson in lessons)
    else:
        lesson_text = 'Нет занятий в ближайшие 48 часов. Проверьте календарь в Teaching Panel.'

    text = (
        '📅 *Ближайшие уроки*\n\n'
        f"{lesson_text}\n\n"
        'Перейдите в веб-приложение, чтобы увидеть полный календарь.'
    )

    await _send_response(update, context, text, reply_markup=_build_section_keyboard('lessons'))


async def show_homework_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _get_linked_user(update, context)
    if not user:
        return

    if user.role == 'teacher':
        submissions = await _fetch_teacher_submissions(user, limit=5)
        if not submissions:
            content = 'Новых сдач, которые ждут проверки, пока нет.'
        else:
            rows = []
            for submission in submissions:
                student_name = _format_display_name(submission.student)
                lesson = submission.homework.lesson
                group_name = lesson.group.name if lesson and lesson.group else 'Без группы'
                submitted_local = timezone.localtime(submission.submitted_at) if submission.submitted_at else None
                submitted_str = submitted_local.strftime('%d.%m %H:%M') if submitted_local else 'неизвестно'
                rows.append(
                    f"• {submission.homework.title}\n"
                    f"  {student_name} · {group_name}\n"
                    f"  Сдано: {submitted_str}"
                )
            content = '\n\n'.join(rows)

        text = (
            '📝 *Домашние задания (учитель)*\n\n'
            f"{content}\n\n"
            'Откройте раздел "Домашка" в Teaching Panel, чтобы выставить оценки.'
        )
    else:
        homeworks = await _fetch_student_homeworks(user, limit=5)
        if not homeworks:
            content = 'Пока нет заданий, которые нужно сдать. Посмотрите расписание или спросите учителя.'
        else:
            rows = []
            for hw in homeworks:
                submission = hw.student_submissions[0] if getattr(hw, 'student_submissions', []) else None
                if not submission:
                    status = '⏳ нужно сдать'
                elif submission.status == 'submitted':
                    status = '🟡 проверяется'
                elif submission.status == 'graded':
                    score = submission.total_score or 0
                    status = f'✅ проверено ({score} балл.)'
                else:
                    status = '✍️ в работе'

                lesson = hw.lesson
                group_name = lesson.group.name if lesson and lesson.group else '—'
                rows.append(
                    f"• {hw.title}\n"
                    f"  Группа: {group_name}\n"
                    f"  Статус: {status}"
                )
            content = '\n\n'.join(rows)

        text = (
            '📝 *Домашние задания (ученик)*\n\n'
            f"{content}\n\n"
            'Зайдите в Teaching Panel, чтобы загрузить ответы или посмотреть комментарии.'
        )

    await _send_response(update, context, text, reply_markup=_build_section_keyboard('homework'))


async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, target = query.data.split(':', 1)

    if target == 'root':
        await show_main_menu(update, context)
    elif target == 'lessons':
        await show_lessons(update, context)
    elif target == 'homework':
        await show_homework_digest(update, context)
    elif target == 'notifications':
        await notifications_info(update, context)
    elif target == 'profile':
        await show_profile(update, context)
    elif target == 'help':
        await help_command(update, context)
    else:
        await query.answer('Раздел временно недоступен', show_alert=True)


def _generate_temp_password(length: int = 12) -> str:
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789@$%&*?'
    return get_random_string(length, alphabet)


async def reset_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /reset - мгновенное обновление пароля."""
    db_user = await _get_linked_user(update, context)
    if not db_user:
        return

    if not db_user.telegram_verified:
        await _send_response(
            update,
            context,
            "❌ Telegram ещё не подтверждён. Создайте код в профиле Teaching Panel и отправьте /start <код>.",
            parse_mode=None,
        )
        return

    new_password = _generate_temp_password()

    def _apply_new_password():
        db_user.set_password(new_password)
        db_user.save(update_fields=['password'])
        PasswordResetToken.objects.filter(user=db_user, used=False).update(
            used=True,
            used_at=timezone.now(),
        )

    await sync_to_async(_apply_new_password)()

    message = (
        "✅ Пароль сброшен\n\n"
        f"Email: {db_user.email}\n"
        f"Новый пароль: {new_password}\n\n"
        "Скопируйте пароль, войдите в Teaching Panel и поменяйте его в профиле."
    )

    await _send_response(update, context, message, parse_mode=None)


async def unlink_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /unlink - отвязка аккаунта"""
    telegram_id = str(update.effective_user.id)
    
    try:
        db_user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)

        keyboard = [
            [
                InlineKeyboardButton("✅ Да, отвязать", callback_data='confirm_unlink'),
                InlineKeyboardButton("❌ Отмена", callback_data='cancel_unlink')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"⚠️ Вы уверены, что хотите отвязать аккаунт?\n\n"
            f"📧 Email: {db_user.email}\n\n"
            f"После отвязки вы не сможете восстанавливать пароль через Telegram.",
            reply_markup=reply_markup
        )
    except User.DoesNotExist:
        await update.message.reply_text(
            "❌ Ваш Telegram не привязан ни к одному аккаунту."
        )


async def confirm_unlink_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение отвязки аккаунта"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = str(query.from_user.id)
    
    try:
        db_user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)
        await sync_to_async(unlink_user_telegram)(db_user)
        
        await query.edit_message_text(
            "✅ Аккаунт успешно отвязан от Telegram.\n\n"
            "Вы можете привязать его снова в любое время через /start"
        )
    except User.DoesNotExist:
        await query.edit_message_text("❌ Аккаунт не найден.")


async def cancel_unlink_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена отвязки аккаунта"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Отвязка отменена. Ваш аккаунт остаётся привязанным.")


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о профиле"""
    user = await _get_linked_user(update, context)
    if not user:
        return

    text = (
        "👤 *Ваш профиль*\n\n"
        f"📧 Email: {user.email}\n"
        f"{_role_badge(user)}\n"
        f"👤 Имя: {user.first_name or '—'} {user.last_name or ''}\n"
        f"📱 Telegram ID: `{user.telegram_id or '—'}`\n"
        f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}\n\n"
        "Команды:\n"
        "/reset — сбросить пароль\n"
        "/unlink — отвязать аккаунт"
    )

    await _send_response(update, context, text, reply_markup=_build_section_keyboard('profile', include_refresh=False))


async def notifications_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает текущие настройки уведомлений пользователя."""
    user = await _get_linked_user(update, context)
    if not user:
        return

    settings_obj, _ = await sync_to_async(NotificationSettings.objects.get_or_create)(user=user)
    message = _build_notification_message(user, settings_obj)
    keyboard = _build_notification_keyboard(user, settings_obj)
    await _send_response(update, context, message, reply_markup=keyboard)


async def toggle_notification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, field = query.data.split(':', 1)
    meta = NOTIFICATION_FIELDS_META.get(field)

    if not meta:
        await query.answer('Неизвестная настройка', show_alert=True)
        return

    user = await _get_linked_user(update, context)
    if not user:
        return

    roles = meta.get('roles')
    if roles and user.role != 'admin' and user.role not in roles:
        if 'student' in roles and 'teacher' in roles:
            audience = 'этой роли'
        elif 'student' in roles:
            audience = 'учеников'
        elif 'teacher' in roles:
            audience = 'преподавателей'
        else:
            audience = 'этой роли'
        await query.answer(f'Настройка доступна только для {audience}.', show_alert=True)
        return

    settings_obj, _ = await sync_to_async(NotificationSettings.objects.get_or_create)(user=user)
    new_value = not getattr(settings_obj, field, False)
    setattr(settings_obj, field, new_value)
    await sync_to_async(settings_obj.save)(update_fields=[field, 'updated_at'])

    await query.answer(f"{meta['label']}: {'включено' if new_value else 'выключено'}")
    await notifications_info(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    text = (
        "📚 *Доступные команды*\n\n"
        "/menu — Главное меню\n"
        "/lessons — Ближайшие уроки\n"
        "/homework — Домашние задания\n"
        "/notifications — Настройки уведомлений\n"
        "/profile — Профиль\n"
        "/reset — Сбросить пароль\n"
        "/support — Поддержка (создать/продолжить обращение)\n"
        "/close — Закрыть текущее обращение\n"
        "/chatid — Показать Chat ID (для групп)\n"
        "/bindgroup <код> — Привязать текущую группу к уроку\n"
        "/unlink — Отвязать Telegram\n"
        "/help — Эта справка\n\n"
        "❓ *Как начать:*\n"
        "1. В Teaching Panel откройте Профиль → Безопасность\n"
        "2. Создайте код и отправьте /start <код> в этот чат\n"
        "3. Используйте меню или команды выше для быстрого доступа."
    )
    await _send_response(update, context, text, reply_markup=_build_section_keyboard('help', include_refresh=False))


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /chatid — показать Chat ID текущего чата (для настройки уведомлений в группах)"""
    chat = update.effective_chat
    chat_id = chat.id
    chat_type = chat.type
    chat_title = chat.title or 'Личный чат'
    
    if chat_type in ('group', 'supergroup'):
        text = (
            f"📋 *Chat ID этой группы:*\n"
            f"`{chat_id}`\n\n"
            f"👥 Группа: {chat_title}\n\n"
            "Скопируйте ID и вставьте в настройки регулярного урока "
            "в поле «Chat ID Telegram-группы»."
        )
    elif chat_type == 'channel':
        text = (
            f"📢 *Chat ID канала:*\n"
            f"`{chat_id}`\n\n"
            f"Канал: {chat_title}"
        )
    else:
        text = (
            f"💬 *Это личный чат*\n"
            f"Chat ID: `{chat_id}`\n\n"
            "Для уведомлений в группу — добавьте бота в группу "
            "и отправьте там /chatid"
        )
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def bindgroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /bindgroup <CODE> — привязать текущую группу к регулярному уроку."""
    if not update.message:
        return
    chat = update.effective_chat
    if not chat or chat.type not in ('group', 'supergroup'):
        await update.message.reply_text('ℹ️ Используйте /bindgroup в Telegram-группе.')
        return

    args = context.args if context.args else []
    if not args:
        await update.message.reply_text('❌ Неверный формат. Используйте: /bindgroup <КОД>')
        return

    code = args[0].strip().upper()
    if not code or len(code) < 6:
        await update.message.reply_text('❌ Некорректный код привязки')
        return

    now = timezone.now()

    def bind_in_db():
        try:
            bind = RecurringLessonTelegramBindCode.objects.select_related('recurring_lesson', 'recurring_lesson__teacher').get(code=code)
        except RecurringLessonTelegramBindCode.DoesNotExist:
            return False, 'Код не найден'

        if bind.used_at is not None:
            return False, 'Код уже использован'

        if bind.expires_at and bind.expires_at < now:
            return False, 'Код истёк'

        rl = bind.recurring_lesson
        # Привязываем chat_id к уроку
        rl.telegram_group_chat_id = str(chat.id)
        rl.telegram_notify_to_group = True
        rl.telegram_notify_enabled = True
        rl.save(update_fields=['telegram_group_chat_id', 'telegram_notify_to_group', 'telegram_notify_enabled', 'updated_at'])

        bind.used_at = now
        bind.used_chat_id = str(chat.id)
        bind.save(update_fields=['used_at', 'used_chat_id'])

        return True, rl

    ok, result = await sync_to_async(bind_in_db)()
    if not ok:
        await update.message.reply_text(f'❌ Не удалось привязать группу: {result}')
        return

    rl = result
    teacher_name = rl.teacher.get_full_name() if rl.teacher else ''
    await update.message.reply_text(
        f"✅ Группа привязана к регулярному уроку!\n\n"
        f"📚 {rl.title} — {rl.group.name}\n"
        f"👨‍🏫 {teacher_name}\n"
        f"🆔 Chat ID: {chat.id}\n\n"
        f"Теперь напоминания будут приходить сюда (если включены)."
    )


async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: Optional[User] = None):
    """Запуск поддержки: просим описать проблему, дальше любые сообщения идут в тикет."""
    if not user:
        user = await _get_linked_user(update, context)
        if not user:
            return

    telegram_id = str(update.effective_user.id)
    support_context[telegram_id] = {'ticket_id': None}

    await _send_response(
        update,
        context,
        "🛟 *Поддержка*\n\nОпишите, пожалуйста, что случилось — одним сообщением.\n"
        "Дальше можете дополнять детали следующими сообщениями.\n\n"
        "Закрыть обращение: /close",
        reply_markup=_build_section_keyboard('help', include_refresh=False),
    )


async def close_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    ctx = support_context.get(telegram_id)
    if not ctx or not ctx.get('ticket_id'):
        await _send_response(update, context, "ℹ️ Сейчас нет активного обращения. Чтобы начать: /support")
        support_context.pop(telegram_id, None)
        return

    ticket_id = ctx['ticket_id']

    def close_ticket():
        try:
            ticket = SupportTicket.objects.get(id=ticket_id)
        except SupportTicket.DoesNotExist:
            return False

        ticket.status = 'closed'
        ticket.resolved_at = timezone.now()
        ticket.save(update_fields=['status', 'resolved_at', 'updated_at'])
        return True

    ok = await sync_to_async(close_ticket)()
    support_context.pop(telegram_id, None)
    await _send_response(
        update,
        context,
        "✅ Обращение закрыто." if ok else "ℹ️ Не удалось найти обращение (возможно, уже закрыто).",
    )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обычные сообщения пользователя: если активен режим поддержки — пишем в тикет."""
    if not update.message or not update.message.text:
        return

    telegram_id = str(update.effective_user.id)
    ctx = support_context.get(telegram_id)
    if not ctx:
        return

    user = await _get_linked_user(update, context)
    if not user:
        support_context.pop(telegram_id, None)
        return

    text = update.message.text.strip()
    if not text:
        return

    def create_or_append():
        ticket_id = ctx.get('ticket_id')
        if not ticket_id:
            ticket = SupportTicket.objects.create(
                user=user,
                subject='Обращение из Telegram',
                description=text,
                category='telegram',
                priority='normal',
                user_agent='Telegram',
                page_url='',
            )

            msg = SupportMessage(
                ticket=ticket,
                author=user,
                message=text,
                is_staff_reply=False,
                read_by_user=True,
                read_by_staff=False,
            )
            # Уведомление о новом тикете уже отправится из SupportTicket.save().
            # Чтобы не дублировать вторым уведомлением "новое сообщение" — пропускаем.
            msg._skip_notify_admins = True
            msg.save()

            return ticket.id, True

        try:
            ticket = SupportTicket.objects.get(id=ticket_id)
        except SupportTicket.DoesNotExist:
            return None, False

        msg = SupportMessage.objects.create(
            ticket=ticket,
            author=user,
            message=text,
            is_staff_reply=False,
            read_by_user=True,
            read_by_staff=False,
        )

        if ticket.status == 'waiting_user':
            ticket.status = 'in_progress'
            ticket.save(update_fields=['status', 'updated_at'])

        return msg.ticket_id, False

    ticket_id, is_new_ticket = await sync_to_async(create_or_append)()
    if not ticket_id:
        support_context.pop(telegram_id, None)
        await _send_response(update, context, "❌ Не удалось найти обращение. Начните заново: /support")
        return

    ctx['ticket_id'] = ticket_id
    support_context[telegram_id] = ctx

    if is_new_ticket:
        await _send_response(
            update,
            context,
            f"✅ Принято! Тикет #{ticket_id} создан.\n"
            "Можете дополнять детали следующими сообщениями.\n"
            "Закрыть обращение: /close",
        )
    else:
        await _send_response(update, context, "✅ Сообщение добавлено. Если всё решено — /close")


def main():
    """Запуск бота"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Ошибка: не установлен TELEGRAM_BOT_TOKEN")
        print("Получите токен у @BotFather в Telegram и установите переменную окружения:")
        print("  set TELEGRAM_BOT_TOKEN=your_token_here  (Windows)")
        print("  export TELEGRAM_BOT_TOKEN=your_token_here  (Linux/Mac)")
        return
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", show_main_menu))
    application.add_handler(CommandHandler("lessons", show_lessons))
    application.add_handler(CommandHandler("homework", show_homework_digest))
    application.add_handler(CommandHandler("reset", reset_password))
    application.add_handler(CommandHandler("unlink", unlink_account))
    application.add_handler(CommandHandler("profile", show_profile))
    application.add_handler(CommandHandler("notifications", notifications_info))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("support", support_start))
    application.add_handler(CommandHandler("close", close_support))
    application.add_handler(CommandHandler("chatid", chatid_command))
    application.add_handler(CommandHandler("bindgroup", bindgroup_command))
    
    # Регистрируем обработчики кнопок
    application.add_handler(CallbackQueryHandler(link_account_callback, pattern='^link_account$'))
    application.add_handler(CallbackQueryHandler(confirm_unlink_callback, pattern='^confirm_unlink$'))
    application.add_handler(CallbackQueryHandler(cancel_unlink_callback, pattern='^cancel_unlink$'))
    application.add_handler(CallbackQueryHandler(handle_menu_callback, pattern='^menu:'))
    application.add_handler(CallbackQueryHandler(toggle_notification_callback, pattern='^notif_toggle:'))

    # Текстовые сообщения: используем только для режима поддержки
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Запускаем бота
    print("🤖 Telegram бот запущен!")
    print(f"🌐 Web приложение: {WEBAPP_URL}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
